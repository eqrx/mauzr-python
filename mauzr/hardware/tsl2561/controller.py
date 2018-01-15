""" Controller for tsl2561 devices. """

import mauzr
from mauzr.serializer import Struct as SS

__author__ = "Alexander Sowitzki"

FMAP = ((0, 0, 0), (0x40, 0x01f2, 0x01be), (0x80, 0x214, 0x2d1),
        (0xc0, 0x23f, 0x37b), (0x0100, 0x270, 0x3fe),
        (0x0138, 0x16f, 0x1fc), (0x019a, 0xd2, 0xfb), (0x29a, 0x18, 0x12))


def control(core, cfgbase="tsl2561", **kwargs):
    """ Controller for tsl2561 devices.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict
    """

    cfg = core.config[cfgbase]
    cfg.update(kwargs)

    mqtt = core.mqtt
    base = cfg["base"]
    log = core.logger("<TSL2561@{}>".format(base))
    mqtt.setup_publish(base + "illuminance", SS("!f"), 0)
    mqtt.setup_publish(base + "poll_interval", SS("!I"), 0, cfg["interval"])

    def _on_measurement(_topic, channels):
        if True in [ch > 65000 for ch in channels]:
            log.warning("Sensor saturated")
            return

        channels = [ch * 16 for ch in channels]

        ratio = 0 if not channels[0] else int(channels[1] * 1024 / channels[0])
        ratio = (ratio + 1) >> 1

        for tres, a, b in FMAP:
            if ratio <= tres:
                f = (a, b)
                break

        channels = [ch * fi for ch, fi in zip(channels, f)]
        illuminance = (max(0, channels[0] - channels[1]) + 8192) >> 14
        mqtt.publish(base + "illuminance", illuminance, True)
    mqtt.subscribe(base + "channels", _on_measurement, SS("<HH"), 0)


def main():
    """ Entry point. """

    mauzr.cpython("mauzr", "tsl2561controller", control)
