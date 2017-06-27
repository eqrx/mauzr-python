""" Driver for BME280 devices. """
__author__ = "Alexander Sowitzki"


import struct
import mauzr.hardware.driver
import mauzr.platform.serializer

# pylint: disable=too-many-instance-attributes
class Driver(mauzr.hardware.driver.DelayedPollingDriver):
    """ Driver for BME280 devices.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units**:

        - i2c
        - mqtt

    **Configuration:**

        - **base** (:class:`str`) - Topic base for the sensor.
        - **address** (:class:`int`) - I2C address of the sensor.
        - **interval** (:class:`int`) - Fetch interval in milliseconds.

    **Output Topics:**

        - **/temperature** (``!f``) - Termperature im °C.
        - **/humidity** (``B``) - humidity in %.
        - **/pressure** (``!f``) - pressure in Pascal.
    """

    def __init__(self, core, cfgbase="bme280", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._address = cfg["address"]
        self._base = cfg["base"]

        self._i2c = core.i2c

        self._t1, self._t2, self._t3, self._t4 = [None] * 4
        self._p1, self._p2, self._p3, self._p4 = [None] * 4
        self._p5, self._p6, self._p7, self._p8 = [None] * 4
        self._p9, self._h1, self._h2, self._h3 = [None] * 4
        self._h4, self._h5, self._h6, self._tfine = [None] * 4

        core.mqtt.setup_publish(self._base + "temperature",
                                mauzr.platform.serializer.Struct("!f"), 0)
        core.mqtt.setup_publish(self._base + "pressure",
                                mauzr.platform.serializer.Struct("!f"), 0)
        core.mqtt.setup_publish(self._base + "humidity",
                                mauzr.platform.serializer.Struct("!B"), 0)

        name = "<BME280@{}>".format(self._base)
        mauzr.hardware.driver.DelayedPollingDriver.__init__(self, core, name,
                                                            cfg["interval"],
                                                            12000)

    @mauzr.hardware.driver.guard(OSError, suppress=True, ignore_ready=True)
    def _init(self):
        self._t1, self._t2, self._t3, self._p1, \
            self._p2, self._p3, self._p4, self._p5, \
            self._p6, self._p7, self._p8, self._p9, \
            _, self._h1 = self._i2c.read_register(self._address, 0x88,
                                                  fmt="<HhhHhhhhhhhhBB")

        buf = self._i2c.read_register(self._address, 0xE1, amount=7)
        self._h6 = struct.unpack_from("<b", buf, 6)[0]
        self._h2, self._h3 = struct.unpack("<hB", buf[0:3])
        self._h4 = (struct.unpack_from("<b", buf, 3)[0] << 4) | (buf[4] & 0xf)
        self._h5 = (struct.unpack_from("<b", buf, 5)[0] << 4) | (buf[4] >> 4)
        self._tfine = 0
        self._i2c.write(self._address, [0xf4, 0x3f])

        super()._init()

    @mauzr.hardware.driver.guard(OSError, suppress=True)
    def _poll(self):
        """ Begin reading a new sample. """

        self._i2c.write(self._address, [0xf2, 1])
        self._i2c.write(self._address, [0xf4, 0x25])
        self._receive_task.enable()

    @mauzr.hardware.driver.guard(OSError)
    def _receive(self):
        """ Finalize reading and publish values. """

        readout = self._i2c.read_register(self._address, 0xf7, amount=8)
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

        self._mqtt.publish(self._base + "temperature", temp / 100, True)
        self._mqtt.publish(self._base + "pressure", pres // 256, True)
        self._mqtt.publish(self._base + "humidity", hum // 1024, True)
