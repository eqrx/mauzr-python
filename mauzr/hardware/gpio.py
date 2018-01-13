"""  Helper for GPIO. """

import mauzr.serializer

__author__ = "Alexander Sowitzki"


def link_output(core, cfgbase="gpioout", **kwargs):
    """ Links a GPIO output to an MQTT topic.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units**:

        - mqtt
        - gpio

    **Configuration:**

        - **topic** (:class:`str`) - Output topic.
        - **pin** (:class:`str`) - Pin to connect.
        - **qos** (:class:`int`) - QoS for the publish, 0-2.

    **Output topics:**

        - ``topic`` (``?``) - GPIO readout.
    """

    cfg = core.config[cfgbase]
    cfg.update(kwargs)
    core.gpio.setup_output(cfg["pin"])

    def _on_setting(_topic, value):
        core.gpio[cfg["pin"]] = value

    core.mqtt.subscribe(cfg["topic"], _on_setting,
                        mauzr.serializer.Bool, cfg["qos"])


def link_input(core, cfgbase="gpioin", **kwargs):
    """ Links a GPIO input to an MQTT topic.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units**:

        - mqtt
        - gpio

    **Configuration:**

        - **topic** (:class:`str`) - Input topic.
        - **pin** (:class:`str`) -  Pin to connect
        - **qos** (:class:`int`) - QoS for the publish, 0-2.
        - **edge** (:class:`str`) - Level changes to publish to. \
                                    May be "none", "rising", "falling" \
                                    or "both".
        - **pull** (:class:`str`) -  Enable internal pullup or pulldown.
                                     May be "none", "up" or "down".

    **Input topics:**

        - ``topic`` (``?``) -  The value of the GPIO pin.
    """

    cfg = core.config[cfgbase]
    cfg.update(kwargs)
    core.gpio.setup_input(cfg["pin"], cfg["edge"], cfg["pull"])
    core.mqtt.setup_publish(cfg["topic"], mauzr.serializer.Bool,
                            cfg["qos"], default=core.gpio[cfg["pin"]])
    current = None
    last = None

    def _on_stable():
        nonlocal last
        if current != last:
            last = current
            core.mqtt.publish(cfg["topic"], current, True)

    task = core.scheduler(_on_stable, 20, single=True)

    def _on_setting(pin, value):
        nonlocal current

        if pin == cfg["pin"]:
            current = value
            task.enable()

    core.gpio.listeners.append(_on_setting)


def link_output_set(core, cfgbase="gpioout", **kwargs):
    """ Links a GPIO input to an MQTT topic.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units**:

        - mqtt
        - gpio

    **Configuration:**

        - **topic** (:class:`str`) - Input topic.
        - **format** (:class:`str`) - Struct format of the message.
        - **pins** (:class:`list`) - Pins to connect.
        - **pwm** (:class:`bool`) - Info if PWMs are used.
        - **qos** (:class:`int`) - QoS for the publish, 0-2.

    **Input topics:**

        - ``topic`` (``?``) -  The value of the GPIO pin.
    """

    cfg = core.config[cfgbase]
    cfg.update(kwargs)

    pins = cfg["pins"]
    [core.gpio.setup_output(pin, pwm=cfg["pwm"]) for pin in pins]

    def _on_setting(_topic, value):
        for pin, v in zip(pins, value):
            core.gpio[pin] = v

    core.mqtt.subscribe(cfg["topic"], _on_setting,
                        mauzr.serializer.Struct(cfg["format"]),
                        cfg.get("qos", 0))
