""" Common base for MQTT clients. """

import logging

__author__ = "Alexander Sowitzki"


class Manager:
    """ Connect to an MQTT broker to exchange messages via topics.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Configuration:**

        - *hosts* - A list of dicts containing host, port, user, password, and
          path to the CA certificiate.

    """

    def __init__(self, core, cfgbase="mqtt", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._core = core

        self._log = logging.getLogger("<MQTT Manager>")

        self.mqtt = None

        self._hosts = cfg["hosts"]
        self._current_config = min(1, len(self._hosts)-1)

        self._subscriptions = {}
        self._publications = {}

        self.connected = False
        self._host_task = core.scheduler(self._next_host, 10000, single=False)
        self._host_task.enable(instant=True)

        self.connection_listeners = []

        core.add_context(self)

    def __enter__(self):
        self.mqtt.set_host(**self._hosts[0])
        return self

    def __exit__(self, *exc_details):
        pass

    def _next_host(self):
        self.mqtt.set_host(**self._hosts[self._current_config])
        self._current_config = min(self._current_config+1, len(self._hosts)-1)

    def _setup_session(self):
        self._log.warning("Session missing, publishing default values")

        # Publish default values
        for c in self._publications.values():
            if c["default"] is not None:
                self.mqtt.publish(c["topic"], c["default"], c["qos"], True)

    def on_connect(self, session_present):
        """ Subscribe all subscriptions.

        :param session_present: True if the MQTT session is already created.
        :type session_present: bool
        """

        self.connected = True
        self._host_task.disable()
        self._log.info("Connected")

        for config in self._subscriptions.values():
            self.mqtt.subscribe(config["topic"], config["qos"])

        if not session_present:
            self._setup_session()

        [listener(True) for listener in self.connection_listeners]

    def on_disconnect(self, reason=None):
        """ React to disconnections from the broker. """

        self.connected = False
        self._log.warning("Disconnected: %s", reason)
        self._host_task.enable(instant=True)

        [listener(False) for listener in self.connection_listeners]

    def on_message(self, topic, payload, retained):
        """ Handle messages received via the mqtt broker.

        :param topic: Topic of the message.
        :type topic: str
        :param payload: Payload of the message.
        :type payload: object
        :param retained: If True this is a retained message.
        :type retained: bool
        :raises Exception: Errors of callback.
        """

        # Fetch information and dispatch callback
        config = self._subscriptions[topic]
        # Deserialize if serializer configured
        if config["serializer"] is not None:
            try:
                payload = config["serializer"].unpack(payload)
            except Exception:
                self._log.error("Error deserializing value "
                                "%s for topic %s", payload, topic)
                raise
        self._log.debug("Received %s: %s", topic, payload)

        try:
            # Inform all callbacks
            [cb(topic, payload) for cb in config["callbacks"]]
        except Exception as err:
            self._log.error("Exception %s for %s. Terminating.",
                            err, config["topic"])
            # Inform core about failure
            self._core.on_failure()
            # Raise exception to the mqtt handler (May be ignored)
            raise

    @staticmethod
    def _verify_topic(topic):
        if "+" in topic or "#" in topic:
            raise NotImplementedError("Wildcards are currently "
                                      "not supported in topics")

    def subscribe(self, topic, callback, serializer, qos):
        """ Subscribe to a topic.

        :param topic: Topic to subscribe to. Currently wildcard subcriptions
                      are only supported for whole subdirectories, e.g. a/#,
                      not a/+, a/+/b or a/#/b. If doing so you may not
                      subscribe to a topic in this directory explicitly.
        :type topic: str
        :param callback: Callback to call when a message is received.
                         Is called with topic and the (deserialized) message
                         data as arguments.
        :type callback: function
        :param serializer: Serializer that converts incoming values. If None,
                           value is passed unprocessed.
        :type serializer: object
        :param qos: QoS level to request.
        :type qos: int
        :raises ValueError: If topic is invalid or already configured in a
                            conflicting manner.
        """

        self._verify_topic(topic)

        config = None
        if topic in self._subscriptions:
            # Topic already subscribed, compare configuration.
            config = self._subscriptions[topic]
            if qos != config["qos"] or serializer != config["serializer"]:
                raise ValueError("Topic {} is already subscribed "
                                 "with other settings".format(topic))
            config["callbacks"].append(callback)
        else:
            # Topic new, create config
            config = {"topic": topic, "qos": qos, "callbacks": [callback],
                      "serializer": serializer}
            self._subscriptions[topic] = config

    def setup_publish(self, topic, serializer, qos, default=None):
        """ Prepare publishing to a topic.

        :param topic: Topic to publish to. May not contain wildcards.
        :type topic: str
        :param serializer: Serializer that converts outgoing values. If None,
                           value is passed unprocessed.
        :type serializer: object
        :param qos: QoS level to use.
        :type qos: int
        :param default: Value to publish on new sessions. May be None.
        :type default: object
        :raises ValueError: If topic is invalid or is already configured
                            in a conflicting manner.
        """

        if "#" in topic or "+" in topic:
            raise ValueError("Please do not use # or + in topic")

        default = serializer.pack(default) if default is not None else None
        config = {"topic": topic, "serializer": serializer, "qos": qos,
                  "default": default}

        if self._publications.get(topic, config) != config:
            raise ValueError("Topic is already configured with other settings")

        self._publications[topic] = config

    def publish(self, topic, payload, retain):
        """ Publish a value to a topic.

        :param topic: Topic to publish to.
        :type topic: str
        :param payload: Value to publish.
        :type payload: object
        :param retain: True if value shall be retained by the server.
        :type retain: bool
        :returns: Return value of underlying client.
        :rtype: object
        :raises Exception: If paho fails.
        """

        config = self._publications[topic]
        if not self.connected:
            return

        self._log.debug("Publishing %s: %s", topic, payload)
        if config["serializer"] is not None:
            payload = config["serializer"].pack(payload)

        return self.mqtt.publish(topic, payload, config["qos"], retain)
