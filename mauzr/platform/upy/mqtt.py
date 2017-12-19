""" Provide MQTT support. """
__author__ = "Alexander Sowitzki"

import gc # pylint: disable=import-error
import ussl # pylint: disable=import-error
from utime import ticks_ms, ticks_diff, sleep_ms # pylint: disable=import-error
#import _thread
from umqtt.simple import MQTTClient # pylint: disable=import-error
from umqtt.simple import MQTTException # pylint: disable=import-error

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

        self._pycom = core.pycom
        self._log = core.logger("<MQTT Client>")
        self._base = cfg["base"]
        self._keepalive = cfg["keepalive"]
        self._clean_session = not cfg.get("session", True)
        self.manager = None
        self._mqtt = None
        self._status_topic = None
        self._connected = False
        self._active = True
        self._last_send = None

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
        # Startup.
        try:
            import _thread
            _thread.start_new_thread(self.manage, [])
        except ImportError:
            pass

        return self

    def __exit__(self, *exc_details):
        # Shutdown.
        self._active = False

    def _disconnect(self, reason=None):
        if self._connected:
            try:
                self._mqtt.publish(self._status_topic, b'\x00', True, 1)
                # Disconnect cleanly
                self._mqtt.disconnect()
            except OSError:
                pass
        self._connected = False
        self.manager.on_disconnect(reason)

    def _connect(self):
        # Connect to the message broker.

        self._log.info("Connecting")

        cfg = self._servercfg
        ca = cfg.get("ca", None)


        ssl_params = None
        if ca:
            ssl_params = {"cert_reqs": ussl.CERT_REQUIRED, "ca_certs": ca}

        user = cfg["user"]
        self._status_topic = "{}agents/{}".format(self._base, user)

        self._mqtt = MQTTClient(server=cfg["host"], port=cfg["port"],
                                client_id=user,
                                keepalive=self._keepalive // 1000,
                                user=user, password=cfg["password"],
                                ssl_params=ssl_params, ssl=ca)

        # Set last will
        self._mqtt.set_last_will(self._status_topic, b'\x00', True, 1)
        # Set the message callback
        self._mqtt.set_callback(self._on_message)
        # Perform connect
        session_present = self._mqtt.connect(clean_session=self._clean_session)
        # Connect done, reduce timeout of socket
        self._mqtt.sock.settimeout(self._keepalive // 8)
        # Publish presence message
        self._mqtt.publish(self._status_topic, b'\xff', True, 1)

        self._connected = True

        # Inform manager
        self.manager.on_connect(session_present)

    def _on_message(self, topic, message, retained):
        # Called when a message was received.

        # Call manager
        self.manager.on_message(topic.decode(), message, retained)
        # Clean up
        gc.collect()

    def _is_elapsed(self, ts, thres):
        now = ticks_ms()
        d = ticks_diff(ts, now) if self._pycom else ticks_diff(now, ts)
        return d > thres

    def manage(self, call_scheduler=False):
        """ Perform client management. """

        while self._active:
            try:
                self._connect()
                last_ping = ticks_ms()
                max_ping = self._keepalive // 2
                last_pong = ticks_ms()
                max_pong = self._keepalive
                while self._active:
                    try:
                        operation = self._mqtt.check_msg()
                        if operation is not None:
                            last_pong = ticks_ms()
                        else:
                            if self._is_elapsed(last_ping, max_ping):
                                last_ping = ticks_ms()
                                self._mqtt.ping()
                            if self._is_elapsed(last_pong, max_pong):
                                raise MQTTException("Keepalive timeout")
                    except OSError as err:
                        if str(err) != "Keepalive timeout":
                            raise

                        if call_scheduler:
                            next_task = self._scheduler.handle(block=False)
                            if next_task is None:
                                call_scheduler = False
                            else:
                                timeout = min(self._keepalive // 8, next_task)
                                self._mqtt.sock.settimeout(timeout)
            except (OSError, MQTTException) as err:
                # Error happened, assume disconnect
                self._disconnect(err)
                begin = ticks_ms()
                if not call_scheduler:
                    sleep_ms(3000)
                while call_scheduler and not self._is_elapsed(begin, 3000):
                    next_task = self._scheduler.handle(block=False)
                    if next_task is None:
                        sleep_ms(100)
                    else:
                        sleep_ms(next_task)
        self._disconnect()

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
        self._last_send = ticks_ms()
        return result
