""" Common base for MQTT clients. """
__author__ = "Alexander Sowitzki"

import logging

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

        if "client_id" not in cfg:
            cfg["client_id"] = "-".join(core.config["id"])
        if "status_topic" not in cfg:
            topic = cfg["base"] + "agents/" + cfg["client_id"]
            cfg["status_topic"] = topic

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
        self._delayed_publishes = []

    def __enter__(self):
        self.mqtt.set_host(**self._hosts[0])
        self.mqtt.__enter__()
        return self

    def __exit__(self, *exc_details):
        return self.mqtt.__exit__(*exc_details)

    def _next_host(self):
        self.mqtt.set_host(**self._hosts[self._current_config])
        self._current_config = min(self._current_config+1, len(self._hosts)-1)

    def on_connect(self, *details):
        """ Subscribe all subscriptions. """

        self.connected = True
        self._host_task.disable()
        self._log.info("Connected")
        # Resubscribe subscriptions after reconnect
        for config in self._subscriptions.values():
            self.mqtt.subscribe(config["topic"], config["qos"])

        for delayed in self._delayed_publishes:
            self.publish(*delayed)
        self._delayed_publishes = []

        [listener(True) for listener in self.connection_listeners]

    def on_disconnect(self, *details):
        """ React to disconnections from the broker. """

        self.connected = False
        self._log.warning("Disconnected")
        self._host_task.enable(instant=True)

        [listener(False) for listener in self.connection_listeners]

    def on_message(self, topic, payload):
        """ Handle messages received via the mqtt broker.

        :param topic: Topic of the message.
        :type topic: str
        :param payload: Payload of the message.
        :type payload: object
        :raises Exception: Errors of callback.
        """

        if topic not in self._subscriptions:
            return

        # Fetch information and dispatch callback
        config = self._subscriptions[topic]
        try:
            # Deserialize if serializer configured
            if config["serializer"] is not None:
                try:
                    payload = config["serializer"].unpack(payload)
                except Exception:
                    self._log.error("Error deserializing value "
                                    "%s for topic %s",
                                    payload, topic)
                    raise
            self._log.debug("Received %s: %s", topic, payload)
            # Inform all callbacks
            for callback in config["callbacks"]:
                callback(topic, payload)
        except Exception:
            self._log.error("Exception for %s. Terminating.", config["topic"])
            # Inform core about failure
            self._core.on_failure()
            # Raise exception to the mqtt handler (May be ignored)
            raise

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

        if "+" in topic or "#" in topic[:-1]:
            raise ValueError("No wildcards allowed except # at end of topic")

        if topic.endswith("#"):
            if topic[-2] != "/":
                raise ValueError("If last topic char is #, "
                                 "previous char must be /")
            directory = topic[:-2]
            for other_topic in self._subscriptions:
                if other_topic.startswith(directory):
                    raise ValueError("When using wildcards you may not "
                                     "to any topic in the target directory "
                                     "explicitly")

        config = None
        if topic in self._subscriptions:
            # Topic already subscribed, compare configuration.
            config = self._subscriptions[topic]
            if qos != config["qos"] or serializer != config["serializer"]:
                raise ValueError("Topic {} is already subscribed "
                                 "with other settings".format(topic))
        else:
            # Topic new, create config
            config = {"topic": topic, "qos": qos, "callbacks": [],
                      "serializer": serializer}
            self._subscriptions[topic] = config

        config["callbacks"].append(callback)

    def setup_publish(self, topic, serializer, qos):
        """ Prepare publishing to a topic.

        :param topic: Topic to publish to. May not contain wildcards.
        :type topic: str
        :param serializer: Serializer that converts outgoing values. If None,
                           value is passed unprocessed.
        :type serializer: object
        :param qos: QoS level to use.
        :type qos: int
        :raises ValueError: If topic is invalid or ist already configured
                            in a conflicting manner.
        """

        if "#" in topic or "+" in topic:
            raise ValueError("Please do not use # or + in topic")

        config = None
        if topic in self._publications:
            # Topic already used, compare configuration.
            config = self._publications[topic]
            if qos != config["qos"] or serializer != config["serializer"]:
                raise ValueError("Topic is already configured "
                                 "with other settings")
        else:
            # Topic new, create config
            config = {"topic": topic, "qos": qos, "serializer": serializer}
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

        if not self.connected:
            self._delayed_publishes.append((topic, payload, retain))

        config = self._publications[topic]
        self._log.debug("Publishing %s: %s", topic, payload)

        if config["serializer"] is not None:
            try:
                payload = config["serializer"].pack(payload)
            except Exception:
                self._log.error("Error serializing value %s for topic %s",
                                payload, topic)
                raise

        return self.mqtt.publish(topic, payload, config["qos"], retain)
