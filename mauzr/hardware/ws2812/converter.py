""" Converter for WS2812 leds. """

import numpy  # pylint: disable=import-error
import mauzr
from mauzr.serializer import Struct as SS

__author__ = "Alexander Sowitzki"


def convert(core, cfgbase="ws2812", **kwargs):
    """ Converter for WS2812 leds.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict
    """

    cfg = core.config[cfgbase]
    cfg.update(kwargs)

    amount = sum([s["length"] for s in cfg["slices"]])
    byte_topic = cfg.get("byte_topic", None)
    spi_topic = cfg.get("spi_topic", None)
    colors = numpy.zeros(amount*3, dtype=numpy.uint8)

    if byte_topic:
        core.mqtt.setup_publish(byte_topic, None, 0)
    if spi_topic:
        buf = numpy.zeros(amount*4*3, dtype=numpy.uint8)
        core.mqtt.setup_publish(spi_topic, None, 0)

    def _on_msg(topic, data):
        o = [s["offset"]*3 for s in cfg["slices"] if s["topic"] == topic][0]
        for i in range(0, len(data), 3):
            colors[o+i:o+i+3] = [int(v*255) for v in data[i:i+3]]

        if byte_topic:
            core.mqtt.publish(byte_topic, colors.tobytes(), True)
        if spi_topic:
            for i in range(4):
                buf[3-i::4] = (((colors >> (2*i+1)) & 1) * 96 +
                               ((colors >> (2*i)) & 1) * 6 + 136)
            core.mqtt.publish(spi_topic, buf.tobytes(), True)

    [core.mqtt.subscribe(sc["topic"], _on_msg, SS("!"+"fff"*sc["length"]), 0)
     for sc in cfg["slices"]]


def main():
    """ Entry point. """

    mauzr.cpython("mauzr", "ws2812converter", convert)
