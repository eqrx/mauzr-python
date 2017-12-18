""" Driver for WS2812 leds. """

def driver(core, cfgbase="ws2812", **kwargs):
    """ Driver for WS2812 leds.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict
    """

    spi = core.spi # Baudrate must be 3_200_000

    cfg = core.config[cfgbase]
    cfg.update(kwargs)

    core.mqtt.subscribe(cfg["topic"], lambda t, v: spi.writer(list(v)), None, 0)
