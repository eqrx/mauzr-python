"""  Helper for GPIO. """
__author__ = "Alexander Sowitzki"

import mauzr.platform.serializer

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
                        mauzr.platform.serializer.Bool, cfg["qos"])

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
    core.mqtt.setup_publish(cfg["topic"], mauzr.platform.serializer.Bool,
                            cfg["qos"])
    core.gpio.setup_input(cfg["pin"], cfg["edge"], cfg["pull"])

    def _on_setting(pin, value):
        if pin == cfg["pin"]:
            core.mqtt.publish(cfg["topic"], value, True)

    core.gpio.listeners.append(_on_setting)
