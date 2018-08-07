""" MQTT connection facilities. """

import threading
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
        log (logging.Logger): Logger to use.
        default_id (int): Next package ID to use if it is not set or invalid.
        factory (callable): Callable for shelf creation.
    """

    def __init__(self, shell, log, default_id, factory=shelve.open):
        self.log = log
        self.path = str(shell.args.data_path/"qos")
        self.default_id = default_id
        self.shelf = None
        interval = shell.args.sync_interval
        self.sync_task = shell.sched.every(interval, self.sync)
        self.factory = factory
        self.all_sent_event = threading.Event()

    def sync(self):
        """ Sync this shelf. """

        self.shelf.sync()

    def clear(self):
        """ Clear all messages from the dict. """

        pkg_id = self.shelf["pkg_id"]
        self.shelf.clear()
        self.shelf["pkg_id"] = pkg_id
        self.update_all_sent()

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

        assert self.shelf is None

        self.shelf = self.factory(self.path)
        self.shelf.setdefault("pkg_id", self.default_id)
        self.update_all_sent()

        self.sync_task.enable()
        return self

    def __exit__(self, *exc_details):
        self.sync_task.disable()
        if self.shelf is not None:
            self.shelf.close()
            self.shelf = None

    def __setitem__(self, pkg_id, msg):
        """ Add a package to the shelf.

        Args:
            pkg_id (int): ID of the new package.
            msg (bytes): Message to store.
        """

        assert isinstance(pkg_id, int)
        self.shelf[str(pkg_id)] = msg
        self.update_all_sent()

    def update_all_sent(self):
        """ Update the all sent event. """

        if self.shelf is not None and len(self.shelf) != 1:
            self.all_sent_event.clear()
        else:
            self.all_sent_event.set()

    def __getitem__(self, pkg_id):
        return self.shelf[str(pkg_id)]

    def __delitem__(self, pkg_id):
        """ Delete a package from the shelf.

        Args:
            pkg_id (int): Package ID to delete.
        """

        assert pkg_id != "pkg_id"
        try:
            del self.shelf[str(pkg_id)]
        except KeyError:
            self.log.warning("Unknown package was confirmed: %s", pkg_id)
        self.update_all_sent()


def default_socket_factory(log, domain, ca, crt, key):  # pragma: no cover
    """ Create a factory for server connection info generators.

    Args:
        log (logging.Logger): Logger to use.
        domain (str): Domain to connect to.
        ca (str): Certificate authority to use.
        crt (str): Certificate file for the client.
        key (str): Key file for the client.
    Returns:
        callable: Factory that returns a generrator for server connection info.\
                  The generator returns tuples containing hostname, port and \
                  CA for TLS.
    """

    query = f"_secure-mqtt._tcp.{domain}"

    ctx = ssl.SSLContext()
    ctx.load_verify_locations(cafile=ca)
    ctx.load_cert_chain(certfile=crt, keyfile=key)
    ctx.set_ciphers("HIGH")
    ctx.set_alpn_protocols(("mqtt/3.1.1",))
    ctx.verify_mode = ssl.CERT_REQUIRED
    #ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = True

    def _new():
        while True:
            for record in dns.resolver.query(query, 'SRV'):
                host, port = str(record.target), record.port
                # Open socket and perform handshake
                log.debug("Opening Socket to %s:%s", host, port)
                try:
                    sock = socket.create_connection((host, port))
                    yield ctx.wrap_socket(sock, server_hostname=host.strip("."))
                except (ValueError, OSError):
                    log.exception("Establishing Connection failed")
                    yield None
    return _new


class Connector:
    """ Connects to an MQTT server and communicates with it.

    Args:
        shell (mauzr.shell.Shell): Shell instance to use.
        socket_factory (callable): Factory for sockets.
        shelf_factory (callable): Factory method for creating the QoS shelf.
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
        self.socket_factory = socket_factory(self.log, args.domain,
                                             args.ca, args.crt, args.key)()
        self.handles = weakref.WeakValueDictionary()  # Dict of topic handles.
        self.connection_listeners = []  # Listeners for connection changes.
        self.qos_shelf = shelf_factory(shell, self.log, 2)  # QoS storage.


        # Prepare packages.
        will_args = {"will_topic": "status/" + args.name, "will_qos": 0,
                     "will_payload": b'\x00', "will_retain": True}
        self.disconnect_pkg = Disconnect(will_pkg_id=1, **will_args)
        self.connect_pkg = Connect(clean_session=False, keepalive=keepalive,
                                   will_pkg_id=0, client_id=args.name,
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
        # Ensure disconnected.
        self.disconnect(await_all_sent=True, reconnect=False)
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
        """ Connect to the mqtt server. """

        # Perform connect.
        try:
            # Open socket and perform handshake
            self.sock = next(self.socket_factory)
            if self.sock is None:
                return
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
        except OSError:
            self.log.exception("Connection failed")
            self.disconnect()

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

    def disconnect(self,
                   await_all_sent=False, reconnect=True):  # pragma: no cover
        """ Disconnect from server. """

        if self.sock is None:
            # Already disconnected.
            return

        if self.sock is not None and await_all_sent:
            self.qos_shelf.all_sent_event.wait(3.0)

        # Set tasks.
        self.ping_task.disable()
        self.timeout_task.disable()
        if reconnect:
            self.connect_task.enable()
        else:
            self.connect_task.disable()
        self.sched.idle(time.sleep)

        self.log.debug("Disconnecting")
        try:
            # Send disconnect package.
            self.sock.send(self.disconnect_pkg)
        except OSError:
            pass
        finally:
            # Close sockets
            self.sock = None
            self.log.warning("Disconnected")
            # Inform listeners.
            [cb(False) for cb in self.connection_listeners]

    def publish_handle(self, handle, payload,
                       disconnect_on_error=True):  # pragma: no cover
        """ Publish a payload.

        Args:
            handle (Handle): Handle to publish on.
            payload (bytes): Payload of the message.
            disconnect_on_error (bool): Disconnect if this publish fails.
        Returns:
            Publish: The message that was sent.
        Raises:
            MQTTOfflineError: If not connected to a server.
        """

        return self.publish(handle.topic, payload, handle.qos,
                            handle.retain, disconnect_on_error)

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
            if self.sock is None:
                raise MQTTOfflineError()
            pkg_id = self.qos_shelf.new_pkg_id()
            if not topic.startswith("log/"):
                self.log.debug("Publishing %s with pkg id %s", topic, pkg_id)
        else:
            pkg_id = None
            self.log.debug("Publishing %s", topic)

        # Make message.
        msg = Publish(topic=topic, payload=payload, qos=qos,
                      retain=retain, pkg_id=pkg_id)

        # Store message if QoS requires it.
        if msg.qos > 0:
            self.qos_shelf[msg.pkg_id] = bytes(msg)

        if self.sock is None:
            return False

        # Send message
        try:
            self.sock.send(msg)
            return True
        except OSError:
            if disconnect_on_error:
                self.disconnect()
            return False

    def unsubscribe(self, handle):  # pragma: no cover
        """ Unsubscribe from a topic.

        Args:
            handle (Handle): Handle to unsubscribe.
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
        self.log.debug("Unsubscribing %s with ID %s", handle.topic, pkg_id)
        msg = Unsubscribe(topic=handle.topic, pkg_id=pkg_id)
        try:
            self.sock.send(msg)
        except OSError:
            self.disconnect()
            raise MQTTOfflineError()
        return pkg_id

    def subscribe(self, handle):  # pragma: no cover
        """ Subscribe to a topic.

        Args:
            handle (Handle): Handle to subscribe.
        Returns:
            int: Package ID used to subscribe.
        Raises:
            MQTTOfflineError: If not connected to a server.
        """

        if self.sock is None:
            # Refuse if offline.
            raise MQTTOfflineError()

        # Get Package ID
        assert 0 <= handle.qos <= 2
        pkg_id = self.qos_shelf.new_pkg_id()

        # Create package and send it.
        self.log.debug("Subscribing %s with ID %s", handle.topic, pkg_id)
        sub = Subscribe(topic=handle.topic, qos=handle.qos, pkg_id=pkg_id)
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
        try:
            self.sock.settimeout(duration)
            try:
                op = self.sock.recv(1)[0]
            except (OSError, IndexError):
                return
            self.sock.settimeout(False)
        except OSError:
            self.disconnect()
            return


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
            shelf[rec.pkg_id] = rec
            sock.send(PubRel(id=rec.pkg_id))
            log.debug("Outgoing publish %s received", rec.pkg_id)
        elif PubComp.TYPE == op:
            # Clear QoS shelf.
            comp = PubComp(sock, op)
            del shelf[comp.pkg_id]
            log.debug("Outgoing publish %s completed", comp.pkg_id)
        elif PubAck.TYPE == op:
            pkg_id = PubAck(sock, op).pkg_id
            # Clear QoS shelf.
            del shelf[pkg_id]
            log.debug("Outgoing publish %s acknowledged", pkg_id)
        elif UnsubAck.TYPE == op:
            unsuback = UnsubAck(sock, op)
            # Inform all subscribed handles about unsub.
            [h.on_unsub(unsuback.pkg_id) for h in self.handles.values()]
            log.debug("Unsub %s acknowledged", unsuback.pkg_id)
        elif SubAck.TYPE == op:
            suback = SubAck(sock, op)
            # Inform all subscribed handles about sub.
            [h.on_sub(suback.pkg_id) for h in self.handles.values()]
            log.debug("Sub %s acknowledged", suback.pkg_id)
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
        for h in [h for h in self.handles.values() if ch in h]:
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
            self.log.debug("Storing publish for %s with ID %s",
                           p.topic, p.pkg_id)
            self.qos_shelf[p.id] = p
            self.sock.send(p.rec)
            return

        self.log.debug("Received publish for %s with ID %s", p.topic, p.pkg_id)
        # Find responsible handles and notify them about the publish
        ch = p.topic.split("/")

        for h in [h for h in self.handles.values() if ch in h]:
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
        assert h.topic == topic
        assert h.qos == qos and h.retain == retain and h.ser == ser, \
               f"Conflicting configuration for topic {topic}: qos {h.qos} "\
               f"- {qos}, retain {h.retain} - {retain}, ser {h.ser} - {ser}"
        return h
