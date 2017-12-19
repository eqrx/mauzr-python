""" Driver for WS2812 leds. """

import spidev # pylint: disable=import-error

def driver(core, cfgbase="ws2812", **kwargs):
    """ Driver for WS2812 leds.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict
    """

    cfg = core.config[cfgbase]
    cfg.update(kwargs)

    spi = spidev.SpiDev()
    spi.open(cfg["bus"], cfg["device"])

    core.mqtt.subscribe(cfg["topic"], lambda t, v: spi.xfer(list(v), 3200000),
                        None, 0)
