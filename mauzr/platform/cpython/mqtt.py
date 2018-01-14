""" Connect with MQTT brokers. """

import ssl
import paho.mqtt.client

__author__ = "Alexander Sowitzki"


class Client:
    """ Use the Paho MQTT implementation to provide MQTT support.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Configuration:**

        - **base** (:class:`str`): Topic base of the suit.
    """

    def __init__(self, core, cfgbase="mqtt", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._log = core.logger("mqtt-client")

        self.client = paho.mqtt.client.Client()
        self._status_topic = None
        self._clean_session = not cfg.get("session", True)
        self.manager = None

        self._subscriptions = {}
        self._publications = {}

        self._keepalive = cfg["keepalive"]
        core.add_context(self)

    def __enter__(self):
        # Start the connector.

        self.client.loop_start()

    def set_host(self, **kwargs):
        """ Set host to connect to.

        :param kwargs: Host Configuration
        :type kwargs: dict
        """

        user = kwargs["user"]
        self._status_topic = "{}/agents/{}".format(user.split("-")[0], user)
        self.client.reinitialise(client_id=user,
                                 clean_session=self._clean_session)
        self.client.username_pw_set(username=user, password=kwargs["password"])
        self.client.will_set(self._status_topic, payload=b'\x00'.decode(),
                             qos=2, retain=True)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        if "ca" in kwargs:
            self.client.tls_set(ca_certs=kwargs["ca"],
                                cert_reqs=ssl.CERT_REQUIRED,
                                tls_version=ssl.PROTOCOL_TLSv1_2,
                                ciphers=None)

        self.client.connect_async(kwargs["host"], kwargs["port"],
                                  self._keepalive // 1000)

    def __exit__(self, *exc_details):
        # Disconnect and stop connector.

        self.client.publish(self._status_topic, payload=b'\x00'.decode(),
                            qos=2, retain=True)
        self.client.loop_stop()
        self.client.disconnect()

    def _on_disconnect(self, *details):
        # Indicate that the client disconnected from the broker.

        self.manager.on_disconnect()

    def _on_connect(self, _client, _userdata, flags, _rc):
        # Indicate that the client connected to the broker.
        self.client.publish(self._status_topic, payload=b'\x01'.decode(),
                            qos=2, retain=True)
        self.manager.on_connect(flags["session present"])

    def _on_message(self, client, userdata, message):
        # Handle messages received via the mqtt broker.

        # Dispatch callback
        self.manager.on_message(message.topic, message.payload, message.retain)

    def subscribe(self, topic, qos):
        """ Subscribe to a topic.

        :param topic: Topic to publish to.
        :type topic: str
        :param qos: QoS level to request.
        :type qos: int
        :returns: Return value from the client.
        :rtype: object
        """

        return self.client.subscribe(topic, qos)

    def publish(self, topic, value, qos, retain):
        """ Publish a value to a topic.

        :param topic: Topic to publish to.
        :type topic: str
        :param value: Value to publish.
        :type value: object
        :param qos: QoS level to use.
        :type qos: int
        :param retain: True if value shall be retained by the server.
        :type retain: bool
        :returns: Return value from the client.
        :rtype: object
        """

        return self.client.publish(topic, value, qos, retain)
