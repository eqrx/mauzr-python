""" Driver for BME280 devices. """

from contextlib import contextmanager
from mauzr.serializer import Struct
from mauzr import Agent, I2CMixin, PollMixin

__author__ = "Alexander Sowitzki"


class LowDriver(I2CMixin, PollMixin, Agent):
    """ Low driver for the BME280. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.output_topic("calibration", r"struct\/!HhhHhhhhhhhhxBhB4s", None,
                          ser=Struct(shell=self.shell, fmt="33s",
                                     desc="Raw calibration data"))
        self.output_topic("output", r"struct\/8s", "Raw measurement")
        self.collect_task = self.after(3, self.collect)

    @contextmanager
    def setup(self):
        # Reset the chip
        self.i2c.write([0xf4, 0x3f])
        # Get calibration data
        c = (self.i2c.read_register(0x88, amount=26) +
             self.i2c.read_register(0xe1, amount=7))
        self.calibrations(c)
        yield
        self.collect_task.disable()

    def poll(self):
        """ Start the measurement and the collection task. """

        self.i2c.write([0xf2, 1])
        self.i2c.write([0xf4, 0x25])
        self.collect_task.enable()

    def collect(self):
        """ Collect the measurement and send it to the high driver. """

        self.output(self._i2c.read_register(0xf7, amount=8))


class HighDriver(Agent):
    """ High driver for the BME280. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_topic("calibration", r"struct\/!HhhHhhhhhhhhxBhB4s",
                         "Raw calibration data", cb=self.on_calibrations)
        self.input_topic("input", r"struct\/8s", "Raw measurement")
        self.output_topic("temperature", r"struct\/!f", "Temperature in °C")
        self.output_topic("pressure", r"struct\/!I", "Air pressure in Pascal")
        self.output_topic("humidity", r"struct\/B", "Air humidity in percent")

        self.h, self.p, self.t = None, None, None
        self.cached_measurement = None

    def on_calibrations(self, cal):
        """ Receive calibrations. """

        from struct import unpack_from as unpack
        self.t = cal[0:3]
        self.p = cal[3:12]
        b = cal[15]
        self.h = cal[12:15] + ((unpack("<b", b, 3)[0] << 4) | (cal[4] & 0xf),
                               (unpack("<b", b, 5)[0] << 4) | (cal[4] >> 4),
                               unpack("<b", b, 6)[0])

        if self.cached_measurement is not None:
            cm = self.cached_measurement
            self.cached_measurement = None
            self.on_input(cm)

    def on_input(self, m):
        """ Convert incoming measurements to usable data. """

        pres = ((m[0] << 16) | (m[1] << 8) | m[2]) >> 4
        temp = ((m[3] << 16) | (m[4] << 8) | m[5]) >> 4
        hum = (m[6] << 8) | m[7]

        values = self.calc_values(hum, pres, temp)
        h, p, t = [v+c for v, c in zip(values, self._corrections)]
        self.temperature(t)
        self.pressure(p)
        self.humidity(h)

    def calc_values(self, hum, pres, temp):
        """ Do the ugly calculations to convert raw into real measurements.

        Args:
            hum (int): Raw humidity measurement.
            pres (int): Raw pressure measurement.
            temp (int): Raw temperature measurement.
        Returns:
            tuple: Converted humidity, pressure and temperature measurements.
        """

        tc, pc, hc = self.t, self.p, self.h

        # temperature
        var1 = ((temp >> 3) - (tc[0] << 1)) * (tc[1] >> 11)
        var2 = (((((temp >> 4) - tc[0]) * ((temp >> 4) - tc[0])) >> 12) *
                tc[2]) >> 14
        tfine = var1 + var2
        temp = ((tfine * 5 + 128) >> 8) / 100

        # pres
        var1 = tfine - 128000
        var2 = var1 * var1 * pc[5] + ((var1 * pc[4]) << 17)
        var2 = var2 + (pc[3] << 35)
        var1 = (((var1 * var1 * pc[2]) >> 8) + ((var1 * pc[1]) << 12))
        var1 = (((1 << 47) + var1) * pc[0]) >> 33
        if var1 == 0:
            pres = 0
        else:
            p = ((((1048576 - pres) << 31) - var2) * 3125) // var1
            var1 = (pc[8] * (p >> 13) * (p >> 13)) >> 25
            var2 = (pc[7] * p) >> 19
            pres = ((p + var1 + var2) >> 8) + (pc[6] << 4) // 256

        # hum
        h = tfine - 76800
        h = (((((hum << 14) - (hc[3] << 20) - (hc[4] * h)) + 16384) >> 15) *
             (((((((h * hc[5]) >> 10) * (((h * hc[2]) >> 11) + 32768)) >> 10) +
                2097152) * hc[1] + 8192) >> 14))
        h = h - (((((h >> 15) * (h >> 15)) >> 7) * hc[0]) >> 4)
        hum = (max(0, min(h, 419430400)) >> 12) // 1024

        return hum, pres, temp
