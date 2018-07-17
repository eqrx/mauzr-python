""" MQTT connection facilities. """

import socket
import ssl
import shelve
import weakref
import time
import dns.resolver
from .messages import Connect, ConnAck, Disconnect, PingReq, PingResp
from .messages import Publish, PubAck, PubRec, PubRel, PubComp
from .messages import Subscribe, SubAck, Unsubscribe, UnsubAck
from .errors import MQTTOfflineError, MQTTProtocolError
from .handle import Handle

__author__ = "Alexander Sowitzki"


class QoSShelf:
    """ Shelf that remebers messages with QoS level > 0.

    Args:
        shell (mauzr.shell.Shell): Shell instance.
        default_id (int): Next package ID to use if it is not set or invalid.
        factory (callable): Callable for shelf creation.
    """

    def __init__(self, shell, default_id, factory=shelve.open):
        self.path = str(shell.args.data_path/"qos")
        self.default_id = default_id
        self.shelf = None
        interval = shell.args.sync_interval
        self.sync_task = shell.sched.every(interval, self.sync)
        self.factory = factory

    def sync(self):
        """ Sync this shelf. """

        self.shelf.sync()

    def clear(self):
        """ Clear all messages from the dict. """

        pkg_id = self.shelf["pkg_id"]
        self.shelf.clear()
        self.shelf["pkg_id"] = pkg_id

    def replay(self):
        """ Get all messages that were not confirmed.

        Yields:
            tuple: Package id and payload.
        """

        msg = [(pkg_id, msg) for pkg_id, msg in self.shelf.items()
               if not pkg_id == "pkg_id" and not isinstance(msg, Publish)]
        for pkg_id, msg in msg:
            msg = bytearray(msg)
            msg[0] |= 0x08
            yield (pkg_id, bytes(msg))

    def new_pkg_id(self):
        """ Get a new package id.

        Returns:
            int: New package ID that can be used for a new message.
        """

        self.shelf["pkg_id"] += 1
        if self.shelf["pkg_id"] > 65535:
            self.shelf["pkg_id"] = self.default_id
        return self.shelf["pkg_id"]

    def __enter__(self):
        """ Open and prepare shelf. """

        self.shelf = self.factory(self.path)
        self.shelf.setdefault("pkg_id", self.default_id)
        self.sync_task.enable()
        return self

    def __exit__(self, *exc_details):
        self.sync_task.disable()
        self.shelf.close()

    def __setitem__(self, pkg_id, msg):
        """ Add a package to the shelf.

        Args:
            pkg_id (int): ID of the new package.
            msg (bytes): Message to store.
        """

        assert isinstance(pkg_id, int)
        self.shelf[str(pkg_id)] = msg

    def __getitem__(self, pkg_id):
        return self.shelf[str(pkg_id)]

    def __delitem__(self, pkg_id):
        """ Delete a package from the shelf.

        Args:
            pkg_id (int): Package ID to delete.
        """

        assert pkg_id != "pkg_id"
        del self.shelf[str(pkg_id)]


def default_socket_factory(log, args):  # pragma: no cover
    """ Create a factory for server connection info generators.

    Args:
        log (logging.Logger): Logger to use.
        ca (str): CA file to use
    Returns:
        callable: Factory that returns a generrator for server connection info.\
                  The generator returns tuples containing hostname, port and \
                  CA for TLS.
    """

    query = f"_secure-mqtt._tcp.{args.server}"

    ctx = ssl.SSLContext()
    ctx.load_verify_locations(cafile=args.ca)
    ctx.load_cert_chain(certfile=args.cert, keyfile=args.key)
    ctx.set_ciphers("HIGH")
    ctx.set_alpn_protocols(("mqtt/3.1.1",))
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = True

    def _new():
        while True:
            for record in dns.resolver.query(query, 'SRV'):
                host, port = str(record.target), record.port
                # Open socket and perform handshake
                log.debug("Opening Socket to %s:%s", host, port)
                sock = socket.create_connection((host, port))
                yield ctx.wrap_socket(sock)
    return _new


class Connector:
    """ Connects to an MQTT server and communicates with it.

    Args:
        shell (mauzr.shell.Shell): Shell instance to use.
        socket_factory (callable): Factory for sockets.
    """

    def __init__(self, shell,
                 socket_factory=default_socket_factory,
                 shelf_factory=QoSShelf):  # pragma: no cover
        # Take program arguments.
        args = shell.args
        keepalive, sched = args.keepalive, shell.sched
        assert keepalive < 65536

        # Setup logger.
        self.log = shell.log.getChild("mqtt")
        self.log.debug("Setting up mqtt")

        # Setup fields.
        self.sched, self.sock = shell.sched, None  # Basics.
        self.socket_factory = socket_factory(self.log, args.ca) # Socket factory.
        self.handles = weakref.WeakValueDictionary()  # Dict of topic handles.
        self.connection_listeners = []  # Listeners for connection changes.
        self.subscribed_handles = set()  # Set of subscribed handles.
        self.qos_shelf = shelf_factory(shell, 2)  # QoS storage.

        # Prepare packages.
        will_args = {"will_topic": "status/" + args.name, "will_qos": 0,
                     "will_payload": b'\x00', "will_retain": True}
        self.disconnect_pkg = Disconnect(will_pkg_id=1, **will_args)
        self.connect_pkg = Connect(clean_session=False, keepalive=keepalive,
                                    will_pkg_id=0, id=args.name,
                                    **will_args)

        # Required tasks-
        self.connect_task = sched.every(args.backoff, self.connect)
        self.timeout_task = sched.after(keepalive, self.on_timeout)
        self.ping_task = sched.every(keepalive*2/3, self.ping)

    def __enter__(self):  # pragma: no cover
        self.qos_shelf.__enter__()  # Prepare shelf.
        self.connect_task.enable(instant=True)  # Enable connecting.
        return self

    def __exit__(self, *exc_details):  # pragma: no cover
        # Disable all tasks.
        self.timeout_task.disable()
        self.ping_task.disable()
        self.connect_task.disable()

        self.disconnect()  # Ensure disconnected.
        self.qos_shelf.__exit__(*exc_details)  # close shelf.

    def ping(self):  # pragma: no cover
        """ Send ping package. """

        self.log.debug("Pinging")
        try:
            self.sock.send(PingReq())
        except OSError:
            self.log.warning("Error on ping")
            self.disconnect()

    def connect(self):  # pragma: no cover
        # Perform connect.
        try:
            # Open socket and perform handshake
            self.sock = self.socket_factory()
            self._handshake()

            # Inform listeners.
            [cb(True) for cb in self.connection_listeners]
            # Set us as idle task.
            self.sched.idle(self._read)
            # Set timers.
            self.connect_task.disable()
            self.timeout_task.enable()
            self.ping_task.enable()
            self.log.info("Connected")
        except OSError as err:
            self.log.warning("Connection failed: %s", str(err))
            self.sock = None

    def _handshake(self):  # pragma: no cover
        """ Perform actual connect with the server. """

        # Exchange connect packages.
        sock = self.sock
        self.log.debug("Sending connect")
        sock.send(self.connect_pkg)
        self.log.debug("Receiving connect")
        op = sock.recv(1)[0]
        if ConnAck.TYPE != op:
            raise MQTTProtocolError(f"Did not receive CONNACK: {op}")

        session_cleared = ConnAck(sock, op).session_cleared
        if session_cleared:
            self.qos_shelf.clear()

        # Publish will.
        self.publish(self.connect_pkg.will_topic, b'\x01', 0, True)
        # Publish packages from QoS shelf.
        for pkg_id, msg in self.qos_shelf.replay():
            self.log.debug("Playing back QoS message %s", pkg_id)
            self.sock.send(msg)
        # Inform handles.
        [h.on_connect(session_cleared) for h in self.handles.values()]

    def on_timeout(self):  # pragma: no cover
        """ Act on ping timeout by disconnecting. """

        self.log.debug("Ping response timed out")
        self.disconnect()

    def disconnect(self):  # pragma: no cover
        """ Disconnect from server. """

        # Set tasks.
        self.ping_task.disable()
        self.timeout_task.disable()
        self.connect_task.enable()
        self.sched.idle(time.sleep)

        if self.sock is None:
            # Already disconnected.
            return

        self.log.debug("Disconnecting")
        try:
            # Send disconnect package.
            self.sock.send(self.disconnect_pkg)
        except (OSError, ConnectionError):
            self.log.warning("Disconnecting gracefully failed")
        finally:
            # Close sockets
            self.sock.close()
            self.sock = None
            self.log.warning("Disconnected")
            # Inform listeners.
            [cb(False) for cb in self.connection_listeners]

    def publish(self, topic, payload, qos,
                retain, disconnect_on_error=True):  # pragma: no cover
        """ Publish a payload.

        Args:
            topic (str): Topic to publish to.
            payload (bytes): Payload of the message.
            qos (int): QoS level.
            retain (bool): Retainment flag.
            disconnect_on_error (bool): Disconnect if this publish fails.
        Returns:
            Publish: The message that was sent.
        Raises:
            MQTTOfflineError: If not connected to a server.
        """

        # Fetch package ID.
        assert 0 <= qos <= 2
        if qos > 0:
            pkg_id = self.qos_shelf.new_pkg_id()
            self.log.debug("Publishing %s with pkg id %s", topic, pkg_id)
        else:
            pkg_id = None
            self.log.debug("Publishing %s", topic)

        # Make message.
        msg = Publish(topic=topic, payload=payload, qos=qos,
                      retain=retain, pkg_id=pkg_id)

        # Store message if QoS requires it.
        if msg.qos > 0:
            self.qos_shelf[publish.pkg_id] = bytes(publish)

        # Send message
        try:
            self.sock.send(msg)
            return msg
        except OSError:
            self.log.warning("Publish failed")
            if disconnect_on_error:
                self.disconnect()
            raise MQTTOfflineError(message=msg)

    def unsubscribe(self, topic):  # pragma: no cover
        """ Unsubscribe from a topic.

        Args:
            topic (str): Topic to unsubscribe from.
        Returns:
            int: Package ID used to unsubscribe.
        Raises:
            MQTTOfflineError: If not connected to a server.
        """

        if self.sock is None:
            # Refuse if offline.
            raise MQTTOfflineError()

        # Get new package ID if not given.
        pkg_id = self.qos_shelf.new_pkg_id()

        # Create and send package.
        self.log.debug("Unsubscribing %s with ID %s", topic, pkg_id)
        msg = Unsubscribe(topic=topic, pkg_id=pkg_id)
        try:
            self.sock.send(msg)
        except OSError:
            self.disconnect()
            raise MQTTOfflineError()
        return pkg_id

    def subscribe(self, topic, qos):  # pragma: no cover
        """ Subscribe to a topic.

        Args:
            topic (str): Topic to subscribe to.
            qos (int): QoS level to request.
        Returns:
            int: Package ID used to subscribe.
        Raises:
            MQTTOfflineError: If not connected to a server.
        """

        if self.sock is None:
            # Refuse if offline.
            raise MQTTOfflineError()

        # Get Package ID
        assert 0 <= qos <= 2
        pkg_id = self.qos_shelf.new_pkg_id()

        # Create package and send it.
        self.log.debug("Subscribing %s with ID %s", topic, pkg_id)
        sub = Subscribe(topic=topic, qos=qos, pkg_id=pkg_id)
        try:
            self.sock.send(sub)
        except OSError:
            self.log.warning("Subscribing failed")
            self.disconnect()
            raise MQTTOfflineError()
        return pkg_id

    def _read(self, duration):  # pragma: no cover
        """ Read message from server.

        Args:
            duration (float): Duration in seconds to block while waiting \
                              for messages.
        Raises:
            MQTTProtocolError: If an invalid message was received from server.
        """

        # Read one byte for the specified duration.
        self.sock.settimeout(duration)
        try:
            op = self.sock.recv(1)[0]
        except OSError:
            return
        finally:
            self.sock.settimeout(False)

        # Reset timeout.
        self.timeout_task.enable()

        sock, shelf, log = self.sock, self.qos_shelf, self.log

        if PingResp.TYPE == op:
            # Timer already reset.
            log.debug("Received ping response")
            buf = self.sock.recv(1)[0]
            assert buf == 0
        elif PubRec.TYPE == op:
            # Convert PUBREC to PUBREL and send it out.
            rec = PubRec(sock, op)
            shelf[rec.id] = rec
            sock.send(PubRel(id=rec.id))
            log.debug("Outgoing publish %s received", rec.id)
        elif PubComp.TYPE == op:
            # Clear QoS shelf.
            comp = PubComp(sock, op)
            del shelf[comp.id]
            log.debug("Outgoing publish %s completed", comp.id)
        elif PubAck.TYPE == op:
            pkg_id = PubAck(sock, op).id
            # Clear QoS shelf.
            del shelf[pkg_id]
            log.debug("Outgoing publish %s acknowledged", pkg_id)
        elif UnsubAck.TYPE == op:
            unsuback = UnsubAck(sock, op)
            # Inform all subscribed handles about unsub.
            [h.on_unsub(unsuback.id) for h in self.subscribed_handles]
            log.debug("Unsub %s acknowledged", unsuback.id)
        elif SubAck.TYPE == op:
            suback = SubAck(sock, op)
            # Inform all subscribed handles about sub.
            [h.on_sub(suback.id) for h in self.subscribed_handles]
            log.debug("Sub %s acknowledged", suback.id)
        elif PubRel.TYPE == op:
            self._handle_incoming_publish_release(op)
        elif Publish.TYPE == op & 0xf0:
            self._handle_incoming_publish(op)
        else:
            raise MQTTProtocolError(f"Received unknown op code: {hex(op)}")

    def _handle_incoming_publish_release(self, op):  # pragma: no cover
        """ Handle an incoming publish release.

        Args:
            op (int): Op code of the following package.
        """

        rel = PubRel(self.sock, op)
        # Pull related publish from storage
        p = self.qos_shelf[rel.id]
        self.log.debug("Received release for publish %s with ID %s",
                       p.topic, rel.id)
        # Find responsible handles and notify them about the publish
        ch = p.topic.split("/")
        for h in [h for h in self.subscribed_handles if ch in h]:
            h.on_publish(p.topic, p.payload, p.retained, p.duplicate)
        # Send PubComp
        self.sock.send(PubComp(rel.id))
        # Forget message
        del self.qos_shelf[rel.id]

    def _handle_incoming_publish(self, op):  # pragma: no cover
        """ Handle an incoming publish.

        Args:
            op (int): Op code of the following package.
        """

        p = Publish(self.sock, op)

        if p.qos == 2:
            self.log.debug("Storing publish for %s with ID %s", p.topic, p.id)
            self.qos_shelf[p.id] = p
            self.sock.send(p.rec)
            return

        self.log.debug("Received publish for %s with ID %s", p.topic, p.id)
        # Find responsible handles and notify them about the publish
        ch = p.topic.split("/")
        for h in [h for h in self.subscribed_handles if ch in h]:
            h.on_publish(p.topic, p.payload, p.retained, p.duplicate)

        if p.qos == 1:
            self.sock.send(p.ack)

    def __call__(self, topic, ser, qos, retain):  # pragma: no cover
        """ Create a handle for a topic.

        Args:
            topic (str): Topic to manage.
            ser (mauzr.serializer.Serializer): Serializer to use for messages.
            qos (int): QoS level for topics.
            retain (bool): Retainment flag.
        Returns:
            mauzr.mqtt.handle.Handle: Created handle.
        """

        if topic not in self.handles:
            return Handle(self, self.sched, topic=topic,
                          ser=ser, qos=qos, retain=retain)
        h = self.handles[topic]
        assert h.qos == qos and h.retain == retain and h.ser == ser
        return h
