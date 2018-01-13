""" Provide MQTT support. """

import gc  # pylint: disable=import-error
from umqtt.simple import MQTTClient  # pylint: disable=import-error
from umqtt.simple import MQTTException  # pylint: disable=import-error

__author__ = "Alexander Sowitzki"


# pylint: disable=too-many-instance-attributes,no-member
class Client:
    """ Provide MQTT support.

    :param core: Core instance.
    :type core: mauzr.core.Core
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Configuration (mqtt section):**

        - **base** (:class:`str`): Topic base of the suit.
    """

    def __init__(self, core, cfgbase="mqtt", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._log = core.logger("<MQTT Client>")
        self._base = cfg["base"]
        self._keepalive = cfg["keepalive"]
        self._clean_session = not cfg.get("session", True)
        self.manager = None
        self._mqtt = None
        self._status_topic = None
        self.connected = False
        self._active = True
        self._last_send = None

        s = core.scheduler

        self._reconnect_task = s(self._reconnect, self._keepalive,
                                 single=False).enable(instant=True)
        self._ping_task = s(self._ping, 5000, single=False)

        s.idle = self._recv

        self._servercfg = None
        self._scheduler = core.scheduler

        core.add_context(self)

    def set_host(self, **kwargs):
        """ Set host to connect to.

        :param kwargs: Host Configuration
        :type kwargs: dict
        """

        self._servercfg = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *exc_details):
        # Shutdown.
        self._active = False

    def _reconnect(self, reason=None):
        self._disconnect(reason)
        try:
            self._connect()
        except OSError as err:
            self._disconnect(err)
            self._reconnect_task.enable(after=3000)

    def _disconnect(self, reason=None):
        self._reconnect_task.disable()
        self._ping_task.disable()
        if self.connected:
            try:
                self._mqtt.publish(self._status_topic, b'\x00', True, 1)
                # Disconnect cleanly
                self._mqtt.disconnect()
            except OSError:
                pass
        self.connected = False
        self.manager.on_disconnect(reason)

    def _connect(self):
        if self.connected:
            raise RuntimeError()
        # Connect to the message broker.

        self._log.info("Connecting")

        cfg = self._servercfg
        ca = cfg.get("ca", None)

        user = cfg["user"]
        self._status_topic = "{}agents/{}".format(self._base, user)

        self._mqtt = MQTTClient(server=cfg["host"], port=cfg["port"],
                                client_id=user,
                                keepalive=self._keepalive // 1000,
                                user=user, password=cfg["password"], ssl=ca)

        # Set last will
        self._mqtt.set_last_will(self._status_topic, b'\x00', True, 1)
        # Set the message callback
        self._mqtt.set_callback(self._on_message)
        # Perform connect
        session_present = self._mqtt.connect(clean_session=self._clean_session)
        # Publish presence message
        self._mqtt.publish(self._status_topic, b'\xff', True, 1)

        self.connected = True

        self._reconnect_task.enable(after=self._keepalive)
        self._ping_task.enable()

        # Inform manager
        self.manager.on_connect(session_present)

    def _on_message(self, topic, message, retained):
        # Called when a message was received.
        self.manager.on_message(topic.decode(), message, retained)
        # Clean up
        gc.collect()

    def _ping(self):
        try:
            self._mqtt.ping()
        except (OSError, MQTTException) as err:
            self._reconnect(err)

    def _recv(self, delay):
        if not self.connected:
            return
        try:
            operation = self._mqtt.wait_msg(delay/1000)
            if operation is not None:
                self._reconnect_task.enable(after=self._keepalive)
        except (OSError, MQTTException) as err:
            self._reconnect(err)

    def subscribe(self, topic, qos):
        """ Subscribe to a topic.

        :param topic: Topic to subscribe to.
        :type topic: str
        :param qos: QoS to use (May be 0 or 1).
        :type qos: int
        :returns: Return value from the client.
        :rtype: object
        :raises ValueError: If QoS is invalid.
        """

        if qos == 2:
            raise ValueError("QoS 2 not supported")
        return self._mqtt.subscribe(topic, qos)

    def publish(self, topic, value, qos, retain):
        """ Publish to a topic.

        :param topic: Topic to publish to.
        :type topic: str
        :param value: Value to publish.
        :type value: bytes
        :param qos: QoS to use (May be 0 or 1).
        :type qos: int
        :param retain: Retain if set to True.
        :type retain: bool
        :returns: Return value from the client.
        :rtype: object
        :raises ValueError: If QoS is invalid.
        """

        if qos == 2:
            raise ValueError("QoS 2 not supported")
        result = self._mqtt.publish(topic, value, retain, qos)
        return result
