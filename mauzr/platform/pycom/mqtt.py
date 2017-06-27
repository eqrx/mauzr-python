""" Provide MQTT support. """
__author__ = "Alexander Sowitzki"

import gc # pylint: disable=import-error
import umqtt # pylint: disable=import-error
import umqtt.simple # pylint: disable=import-error

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

        - *client_id*: MQTT client ID (``str``).
        - *status_topic*: Topic to publish information to.
    """

    def __init__(self, core, cfgbase="mqtt", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        core.add_context(self)

        self._log = core.logger("<MQTT Client>")
        self._agent_topic = cfg["status_topic"]
        self.manager = None
        self._mqtt = None
        self.led = core.led
        self._client_id = cfg["client_id"]

        scheduler = core.scheduler
        self._manage_task = scheduler(self._manage, 50, single=False)
        self._ping_task = scheduler(self._ping, 30000//2, single=False)
        self._pong_task = scheduler(self._pong_timeout, 30000, single=True)
        self._connect_task = scheduler(self._connect, 1000, single=True)
        self._connect_task.enable(instant=True)

        self._connected = False

        self._host = None
        self._port = None
        self._user = None
        self._password = None

    def set_host(self, **kwargs):
        """ Set host to connect to.

        :param kwargs: Host Configuration
        :type kwargs: dict
        """

        self._user = kwargs["user"]
        self._password = kwargs["password"]
        self._host = kwargs["host"]
        self._port = kwargs["port"]

    def __enter__(self):
        # Startup.

        return self

    def __exit__(self, *exc_details):
        # Shutdown.

        # Kill all tasks
        self._connect_task.disable()
        self._ping_task.disable()
        self._pong_task.disable()
        self._manage_task.disable()

        if self._connected:
            try:
                self._mqtt.publish(self._agent_topic, b'\x00', True, 1)
                # Disconnect cleanly
                self._mqtt.disconnect()
            except OSError:
                pass

    def _connect(self):
        # Connect to the message broker.

        try:
            self._log.info("connecting")
            # Create client
            self._mqtt = umqtt.simple.MQTTClient(server=self._host,
                                                 port=self._port,
                                                 client_id=self._client_id,
                                                 keepalive=30,
                                                 user=self._user,
                                                 password=self._password)
            # Set last will
            self._mqtt.set_last_will(self._agent_topic, b'\x00', True, 1)
            # Set the message callback
            self._mqtt.set_callback(self._on_message)
            # Perform connect
            self._mqtt.connect(clean_session=True)
            # Connect done, reduce timeout of socket
            self._mqtt.sock.settimeout(1)
            # Pulish presence message
            self._mqtt.publish(self._agent_topic, b'\xff', True, 1)

            self._connected = True

        except (OSError, umqtt.simple.MQTTException) as err:
            self._log.info("fail: %s", err)
            # Retry later
            self._connect_task.enable()
            return

        self._log.info("success")

        # Enable tasks
        self._ping_task.enable(instant=True)
        self._manage_task.enable(instant=True)

        # Inform manager
        self.manager.on_connect()

    def _on_disconnect(self):
        # Called on client disconnect.

        self._connected = False

        self._log.info("disconnect")
        # Schedule reconnect
        self._connect_task.enable()
        # Disable management tasks
        self._ping_task.disable()
        self._pong_task.disable()
        self._manage_task.disable()

        # Inform manager
        self.manager.on_disconnect()

    def _ping(self):
        # Send a ping.

        self._log.debug("Sending ping")
        try:
            self._mqtt.ping()
            # Schedule pong timeout
            self._pong_task.enable()
        except OSError:
            self._on_disconnect()

    def _pong_timeout(self):
        # Called when a pong was not received in time.

        self._log.error("Disconnect due to timeout")
        self._on_disconnect()

    def _on_message(self, topic, message):
        # Called when a message was received.

        # Blink the LED
        self.led.set(self.led.ACT)
        # Call manager
        self.manager.on_message(topic.decode(), message)
        # Clean up
        gc.collect()

    def _manage(self):
        # Perform client management.

        try:
            while True:
                # Check for messages
                operation = self._mqtt.check_msg()
                # Received message was a pong
                if operation == 208:
                    # Disable pong timeout
                    self._log.debug("Received ping")
                    self._pong_task.disable()
                elif operation is None:
                    # Message queue is empty, let the system so something else
                    break
        except (OSError, umqtt.simple.MQTTException):
            # Error happened, assume disconnect
            self._on_disconnect()

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
        try:
            # Blink LED
            self.led.set(self.led.ACT)
            return self._mqtt.publish(topic, value, retain, qos)
        except OSError:
            self._log.warning("Ignoring publish while offline")
