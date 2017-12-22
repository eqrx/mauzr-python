""" Controller for BME280 devices. """
__author__ = "Alexander Sowitzki"

import struct
import mauzr
from mauzr.serializer import Struct

# pylint: disable=too-many-instance-attributes
class Controller:
    """ Driver for BME280 devices.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    """

    def __init__(self, core, cfgbase="bme280", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._base = cfg["base"]
        self._mqtt = core.mqtt
        self._corrections = cfg.get("corrections", (None, None, None))

        self._t1, self._t2, self._t3, self._t4 = [None] * 4
        self._p1, self._p2, self._p3, self._p4 = [None] * 4
        self._p5, self._p6, self._p7, self._p8 = [None] * 4
        self._p9, self._h1, self._h2, self._h3 = [None] * 4
        self._h4, self._h5, self._h6, self._tfine = [None] * 4

        self._mqtt.subscribe(self._base + "calibrations/pt",
                             self._on_pt_corrections,
                             Struct("<HhhHhhhhhhhhBB"), 0)
        self._mqtt.subscribe(self._base + "calibrations/h",
                             self._on_h_correction, None, 0)
        self._mqtt.subscribe(self._base + "readout", self._on_readout, None, 0)

        self._mqtt.setup_publish(self._base + "temperature", Struct("!f"), 0)
        self._mqtt.setup_publish(self._base + "pressure", Struct("!I"), 0)
        self._mqtt.setup_publish(self._base + "humidity", Struct("B"), 0)
        self._mqtt.setup_publish(self._base + "poll_interval", Struct("!I"), 0,
                                 cfg["interval"])

    def _on_pt_corrections(self, _topic, corrections):
        self._t1, self._t2, self._t3, self._p1, \
            self._p2, self._p3, self._p4, self._p5, \
            self._p6, self._p7, self._p8, self._p9, \
            _, self._h1 = corrections

    def _on_h_correction(self, _topic, buf):
        self._h6 = struct.unpack_from("<b", buf, 6)[0]
        self._h2, self._h3 = struct.unpack("<hB", buf[0:3])
        self._h4 = (struct.unpack_from("<b", buf, 3)[0] << 4) | (buf[4] & 0xf)
        self._h5 = (struct.unpack_from("<b", buf, 5)[0] << 4) | (buf[4] >> 4)
        self._tfine = 0

    def _on_readout(self, _topic, readout):
        if self._t1 is None or self._h6 is None:
            return
        pres = ((readout[0] << 16) | (readout[1] << 8) | readout[2]) >> 4
        temp = ((readout[3] << 16) | (readout[4] << 8) | readout[5]) >> 4
        hum = (readout[6] << 8) | readout[7]

        # temperature
        var1 = ((temp >> 3) - (self._t1 << 1)) * (self._t2 >> 11)
        var2 = (((((temp >> 4) - self._t1) * ((temp >> 4) - self._t1))
                 >> 12) * self._t3) >> 14
        self._tfine = var1 + var2
        temp = (self._tfine * 5 + 128) >> 8

        # pres
        var1 = self._tfine - 128000
        var2 = var1 * var1 * self._p6
        var2 = var2 + ((var1 * self._p5) << 17)
        var2 = var2 + (self._p4 << 35)
        var1 = (((var1 * var1 * self._p3) >> 8) + ((var1 * self._p2) << 12))
        var1 = (((1 << 47) + var1) * self._p1) >> 33
        if var1 == 0:
            pres = 0
        else:
            p = ((((1048576 - pres) << 31) - var2) * 3125) // var1
            var1 = (self._p9 * (p >> 13) * (p >> 13)) >> 25
            var2 = (self._p8 * p) >> 19
            pres = ((p + var1 + var2) >> 8) + (self._p7 << 4)

        # hum
        h = self._tfine - 76800
        h = (((((hum << 14) - (self._h4 << 20) - (self._h5 * h)) + 16384)
              >> 15) * (((((((h * self._h6) >> 10) *
                            (((h * self._h3) >> 11) + 32768)) >> 10) +
                          2097152) * self._h2 + 8192) >> 14))
        h = h - (((((h >> 15) * (h >> 15)) >> 7) * self._h1) >> 4)
        h = 0 if h < 0 else h
        h = 419430400 if h > 419430400 else h
        hum = h >> 12

        for lbl, val, cor in zip(("humidity", "pressure", "temperature"),
                                 (hum // 1024, pres // 256, temp / 100),
                                 self._corrections):
            if cor is not None:
                val += cor
            self._mqtt.publish(self._base + lbl, val, True)

def main():
    """ Main method for the Controller. """
    # Setup core
    core = mauzr.linux("mauzr", "bme280controller")
    # Setup MQTT
    core.setup_mqtt()
    # Spin up controller
    Controller(core)
    # Run core
    core.run()

if __name__ == "__main__":
    main()
