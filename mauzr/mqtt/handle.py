""" Handler for MQTT topics. """

# Store QoS for retained message and retransmit only on QoS > 1

import weakref
from contextlib import suppress
from mauzr.serializer import Serializer, SerializationError
from .errors import MQTTOfflineError

__author__ = "Alexander Sowitzki"


class SubscriptionToken:
    """ Unsubscribes callback when dereferenced & supplies last retained value.

    Args:
        handle (Handle): Hande that was subcribed.
        cb (callable): Callback of the subscription.
    """

    def __init__(self, handle, cb):
        weakref.finalize(self, handle.unsub, cb)


class Handle:
    """ Handler for a single MQTT topic.

    Requires a MQTT connector and a scheduler as positional arguments
    and the following keyword arguments:
    - topic (str):
    - ser (int):
    Optional keyword arguments:
    - retain (bool) -> True: MQTT retainment flag.
    - qos (int) -> 0: MQTT QoS level.
    Additional keyword arguments that should be used by the connector only:
    - retained_value (bytes) -> None: Last known value.
    - sub_id (int) -> None: Currently running subscription request.
    - unsub_id (int) -> None: Currently running unsubscription request.
    - subbed (bool) -> False: If True the topic is already subscribed.
    """

    def __init__(self, mqtt, sched, topic, ser, qos=0, retain=True):
        assert isinstance(ser, Serializer)
        self.mqtt, self.sched = mqtt, sched
        self.sub_id, self.unsub_id = None, None
        self.subbed, self.callbacks = None, {}
        assert isinstance(topic, str)
        self.topic, self.ser, self.chunks = topic, ser, topic.split("/")
        self.qos, self.retain = qos, retain
        self.last_received, self.last_send = None, None
        self.log = mqtt.log.getChild(self.topic)

        assert self.topic not in mqtt.handles
        mqtt.handles[self.topic] = self

    def __hash__(self):
        # Use topic hash for the handle.
        return hash(self.topic)

    def __eq__(self, other):
        if not isinstance(other, Handle) or self.topic != other.topic:
            return False
        assert id(self) == id(other)
        return True

    def __contains__(self, chunks):
        """ Test if this handler match the given topic chunks.

        Args:
            chunks (tuple): topic string split by "/"
        Returns:
            bool: True if handler contains chunks.
        """

        if len(chunks) < len(self.chunks):
            return chunks[-1] == "#"
        elif len(chunks) > len(self.chunks):
            return self.chunks[-1] == "#"
        for l, r in zip(chunks, self.chunks):
            if l != r and "#" not in (l, r) and "+" not in (l, r):
                return False
        return True

    def _sub(self):
        """ Perform actual subscribe with the connector. """

        with suppress(MQTTOfflineError):
            self.sub_id = self.mqtt.subscribe(handle=self)

    def _unsub(self):
        """ Perform actual unsubscribe with the connector. """

        with suppress(MQTTOfflineError):
            self.unsub_id = self.mqtt.unsubscribe(handle=self)

    def on_connect(self, new_session):
        """ To be called when a connection is established to a broker.

        Args:
            new_session(bool): True if current session is clean.
        """

        if new_session and self.callbacks:
            self.subbed = False
            self._sub()

        if new_session and self.last_send is not None:
            self.mqtt.publish(handle=self, payload=self.last_send)

    def change_ser(self, ser):
        """ Change the serializer of this handle.

        Args:
            ser (mauzr.serializer.Serializer): New serializer to use.
        """

        self.ser = ser

    def on_sub(self, pkg_id):
        """ To be called when an sub ack comes in from the broker.

        Args:
            pkg_id(int): ID of the subscription.
        """

        if pkg_id == self.sub_id:
            self.sub_id = None
            self.subbed = True
            self.mqtt.subscribed_handles.add(self)

    def on_unsub(self, pkg_id):
        """ To be called when an unsub ack comes in from the broker.

        Args:
            pkg_id(int): ID of the unsubscription.
        """

        if pkg_id == self.unsub_id:
            self.subbed = False
            self.unsub_id = None
            self.mqtt.subscribed_handles.discard(self)

    def on_publish(self, topic, payload, retained, duplicate):
        """ To be called when a message for this handle arrives.

        Args:
            topic (str): Publish topic.
            payload (bytes): Published payload.
            retained (bool): If this payload was resent because it was retained.
            duplicate (bool): If this message is a retry.
        """

        handle = self

        if "+" in topic or "#" in topic:
            handle = self.mqtt(topic=topic, ser=self.ser,
                               qos=self.qos, retain=self.retain)

        try:
            value = self.ser.unpack(payload)
        except SerializationError:
            self.log.exception("Deserialization failed")
            return

        if retained:
            self.last_received = value

        for cb in self.callbacks:
            self.send_to_cb(cb, value, retained, duplicate, handle)

    def send_to_cb(self, cb, value, retained, duplicate, handle):
        """ Send a value to a given callback. No need to call manually.

        Args:
            cb (callable): Callback to invoke.
            value (object): Value to send.
            retained (bool): If value was retained.
            duplicate (bool): If message is retry.
            handle (Handle): Originating handle.
        """

        wants_handle, delivery = self.callbacks[cb]
        kwargs = {}
        if wants_handle:
            kwargs["handle"] = handle
        if delivery:
            kwargs["retained"] = retained
            kwargs["duplicate"] = duplicate
        cb(value, **kwargs)

    def __call__(self, *payload):
        """ Publish a value to the topic.

        Args:
            payload (object): The value to publish.
        """

        if len(payload) <= 1:
            payload = payload[0]

        payload = self.ser.pack(payload)
        if self.retain:
            self.last_send = payload
        self.mqtt.publish(handle=self, payload=payload)

    def publish_meta(self):
        """ Publish meta data of the topic. """

        mqtt, ser = self.mqtt, self.ser
        chunks = self.chunks
        if "#" in chunks:
            raise RuntimeError("Can not publish meta to topics containing '#'.")

        chunks = [c if c != "+" else "*" for c in chunks]

        mqtt.publish(topic="/".join(["fmt"] + chunks),
                     payload=ser.fmt_payload, qos=1, retain=True)
        mqtt.publish(topic="/".join(["desc"] + chunks),
                     payload=ser.desc_payload, qos=1, retain=True)

    def sub(self, cb, wants_handle=False, wants_delivery=False):
        """ Add a callback for this topic.

        Args:
            cb (callable): Callable to call when a publish arrives.
            wants_handle (bool): If the publish topic shall be included as \
                                 keyword argument "handle" (Handle).
            wants_delivery (bool): If delivery inforation shall be included as \
                                   keyword arguments "retained" (bool) and \
                                   "duplicate" (bool).
        Returns:
            object: Subscription token. If this reference is lost by the \
                    caller, the callback will be automatically unsubscribed.
        """

        was_inactive = not self.callbacks

        # Remember delivery settings.
        self.callbacks[cb] = (wants_handle, wants_delivery)

        # Subscribe if needed.
        if was_inactive:
            self._sub()

        if self.last_received is not None:
            self.send_to_cb(cb, self.last_received, True, True, self)

        return SubscriptionToken(self, cb)

    def unsub(self, cb):
        """ Unsub a callback. Should not be called manually.

        Args:
            cb (callable): Callable to unsub.
        """

        if cb in self.callbacks:
            del self.callbacks[cb]
        if not self.callbacks:
            self._unsub()

    def child(self, topic, ser, qos, retain):
        """ Create a handler for a topic that is below this one.

        Args:
            topic (str): Topic that will be appended to the current one \
                            (with a /).
            ser (Serializer): Serializer of the new handler.
            qos (int): QoS of the new handler.
            retain (bool): Retain of the new handler.
        Returns:
            Handler: New child handler.
        """

        return self.mqtt(topic=f"{self.topic}/{topic}", ser=ser,
                         qos=qos, retain=retain)
