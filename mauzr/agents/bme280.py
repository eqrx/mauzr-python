""" Driver for BME280 devices. """

import struct
from contextlib import contextmanager
from mauzr import Agent, I2CMixin, PollMixin

__author__ = "Alexander Sowitzki"


class LowDriver(I2CMixin, PollMixin, Agent):
    """ Low driver for the BME280. """

    def __init__(self, *args, **kwargs):
        self.collect_task = None
        super().__init__(*args, **kwargs)

        self.output_topic("calibration", r"struct\/32s",
                          "Raw calibration data")
        self.output_topic("output", r"struct\/!HII", "Raw measurement")

        self.update_agent(arm=True)

    @contextmanager
    def setup(self):
        self.collect_task = self.after(3, self.collect)
        # Reset the chip
        self.i2c.write([0xf4, 0x3f])
        a = self.i2c.read_register(0x88, amount=24)
        b = self.i2c.read_register(0xa1, amount=1)
        c = self.i2c.read_register(0xe2, amount=7)
        self.calibration(a+b+c)
        yield
        self.collect_task = None

    def poll(self):
        """ Start the measurement and the collection task. """

        self.i2c.write([0xf2, 1])
        self.i2c.write([0xf4, 0x25])
        self.collect_task.enable()

    def collect(self):
        """ Collect the measurement and send it to the high driver. """

        m = self.i2c.read_register(0xf7, amount=8)

        pressure = ((m[0] << 16) | (m[1] << 8) | m[2]) >> 4
        temperature = ((m[3] << 16) | (m[4] << 8) | m[5]) >> 4
        humidity = (m[6] << 8) | m[7]

        self.output(humidity, pressure, temperature)


class HighDriver(Agent):
    """ High driver for the BME280. """

    def __init__(self, *args, **kwargs):
        self.h, self.p, self.t = None, None, None
        self.cached_measurement = None
        super().__init__(*args, **kwargs)
        self.input_topic("calibration", r"struct\/32s",
                         "Raw calibration data", cb=self.on_calibration)
        self.input_topic("input", r"struct\/!HII", "Raw measurement")
        self.output_topic("temperature", r"struct\/!f", "Temperature in °C")
        self.output_topic("pressure", r"struct\/!I", "Air pressure in Pascal")
        self.output_topic("humidity", r"struct\/B", "Air humidity in percent")

        self.update_agent(arm=True)

    def on_calibration(self, cal):
        """ Receive calibration. """

        self.t = struct.unpack("<Hhh", cal[0:6])
        self.p = struct.unpack("<Hhhhhhhhh", cal[6:24])
        h = list(struct.unpack("<BhB", cal[24:28]))
        h.extend(struct.unpack(">h", cal[28:30]))
        h.extend(struct.unpack("<h", cal[29:31]))
        h.extend(struct.unpack("<b", cal[31:32]))
        self.h = tuple(h)


        self.h = list(cal[12:18])
        self.h[4] = (self.h[4] << 4) | self.h[5] & 0x0f
        self.h[5] = (self.h[5] << 4) | (self.h[5] >> 4) & 0x0f
        self.h = tuple(self.h)
        print(self.h)

        if self.cached_measurement is not None:
            cm = self.cached_measurement
            self.cached_measurement = None
            self.on_input(cm)

    def on_input(self, m):
        """ Convert incoming measurements to usable data. """

        hum, pres, temp = m
        tc, pc, hc = self.t, self.p, self.h

        temp = float(temp)
        var1 = (temp / 16384.0 - float(tc[0]) / 1024.0) * float(tc[1])
        var2 = pow(temp / 131072.0 - float(tc[0]) / 8192.0, 2) * float(tc[2])
        t_fine = int(var1 + var2)
        self.temperature((var1 + var2) / 5120.0)

        pres = float(pres)
        var1 = float(t_fine) / 2.0 - 64000.0
        var2 = var1 * var1 * float(pc[5]) / 32768.0
        var2 = var2 + var1 * float(pc[4]) * 2.0
        var2 = var2 / 4.0 + float(pc[3]) * 65536.0
        var1 = (float(pc[2])*var1*var1/524288.0 + float(pc[1])*var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * float(pc[0])
        if var1 != 0:
            p = 1048576.0 - pres
            p = ((p - var2 / 4096.0) * 6250.0) / var1
            var1 = float(pc[8]) * p * p / 2147483648.0
            var2 = p * float(pc[7]) / 32768.0
            p = p + (var1 + var2 + float(pc[6])) / 16.0
            self.pressure(int(p))

        hum = float(hum)
        h = float(t_fine) - 76800.0
        h = (hum-(float(hc[3])*64.0+float(hc[4])/16384.0* h)) * \
            (float(hc[1])/65536.0* (1.0+float(hc[5])/67108864.0*h
                                    *(1.0+float(hc[2])/67108864.0*h)))
        h = h * (1.0 - float(hc[0]) * h / 524288.0)
        if 0 <= h <= 100:
            self.humidity(int(h))
