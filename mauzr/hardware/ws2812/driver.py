""" Driver for WS2812 leds. """

__author__ = "Alexander Sowitzki"


def _setup_direct(core, cfg):
    import machine  # pylint: disable=import-error
    import neopixel  # pylint: disable=import-error
    import sys

    if sys.platform == "esp32":
        n = neopixel.NeoPixel(machine.Pin(cfg["pin"]), cfg["amount"],
                              timing=True)
    else:
        n = neopixel.NeoPixel(machine.Pin(cfg["pin"]), cfg["amount"])

    def _on_neopixel(_topic, value):
        mv = memoryview(value)
        for i in range(n.n):
            n[i] = mv[i*3:i*3+3]
        n.write()
    core.mqtt.subscribe(cfg["topic"], _on_neopixel, None, 0)


def _setup_spidev(core, cfg):
    import spidev  # pylint: disable=import-error
    spi = spidev.SpiDev()
    spi.open(cfg["bus"], cfg["device"])

    core.mqtt.subscribe(cfg["topic"], lambda t, v: spi.xfer(list(v), 3200000),
                        None, 0)


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

    try:
        _setup_direct(core, cfg)
    except ImportError:
        _setup_spidev(core, cfg)
