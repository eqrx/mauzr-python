""" Controller for tsl2561 devices. """

import mauzr
from mauzr.serializer import Struct as SS

__author__ = "Alexander Sowitzki"


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

        if ratio >= 0 and ratio <= 0x40:
            f = (0x01f2, 0x01be)
        elif ratio <= 0x80:
            f = (0x214, 0x2d1)
        elif ratio <= 0x00c0:
            f = (0x23f, 0x37b)
        elif ratio <= 0x0100:
            f = (0x270, 0x3fe)
        elif ratio <= 0x0138:
            f = (0x16f, 0x1fc)
        elif ratio <= 0x019a:
            f = (0xd2, 0xfb)
        elif ratio <= 0x29a:
            f = (0x18, 0x12)
        else:
            f = (0, 0)

        channels = [ch * fi for ch, fi in zip(channels, f)]
        illuminance = (max(0, channels[0] - channels[1]) + 8192) >> 14
        mqtt.publish(base + "illuminance", illuminance, True)
    mqtt.subscribe(base + "channels", _on_measurement, SS("<HH"), 0)


def main():
    """ Entry point. """

    mauzr.cpython("mauzr", "tsl2561controller", control)
