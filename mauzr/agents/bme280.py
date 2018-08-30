""" Driver for BME280 devices. """

import struct
from contextlib import contextmanager
from mauzr import Agent, I2CMixin, PollMixin

__author__ = "Alexander Sowitzki"

class BME280Calculator:
    """ Calculation methods for BME280. """

    @staticmethod
    def calc_t_fine(reading, tc):
        """ Calculate t_fine.

        Args:
            reading (int): Temperature reading.
            tc (tuple): Temperature calibrations.
        Returns:
            int: Calculated t_fine.
        """

        v1 = (reading / 16 - tc[0]) * tc[1] / 1024
        v2 = pow(reading / 16 - tc[0], 2) * tc[2] / 67108864
        return int(v1 + v2)

    @staticmethod
    def calc_temperature(t_fine):
        """ Calculate temperature.

        Args:
            t_fine (int): T_fine value.
        Returns:
            float: Calculated temperature.
        """

        return t_fine / 5120

    @staticmethod
    def calc_pressure(reading, t_fine, pc):
        """ Calculate pressure.

        Args:
            reading (int): Pressure reading.
            t_fine (int): T_fine value.
            pc (tuple): Pressure calibrations.
        Returns:
            int: Calculated pressure.
        """

        v1 = t_fine / 2 - 64000
        v2 = pow(v1, 2) * pc[5] / 32768 + v1 * pc[4] * 2
        v2 = v2 / 4 + pc[3] * 65536
        v3 = pc[2] * pow(v1, 2) / 524288
        v1 = (1 + (v3 + pc[1] * v1) / 17179869184) * pc[0]
        if not v1:
            return 0

        v2 = (1048576 - reading - v2 / 4096) * 6250 / v1
        v1 = pc[8] * pow(v2, 2) / 2147483648
        return v2 + (v1 + v2 * pc[7] / 32768 + pc[6]) / 16

    @staticmethod
    def calc_humidity(reading, t_fine, hc):
        """ Calculate humidity.

        Args:
            reading (int): Humidity reading.
            t_fine (int): T_fine value.
            hc (tuple): Humidity calibrations.
        Returns:
            int: Humidity percentage.
        """

        v1 = t_fine - 76800
        v2 = reading - hc[3] * 64 - hc[4] / 16384 * v1
        v3 = 1 + hc[2] / 67108864 * v1
        v4 = v2 * hc[1] * (v3 * (1 + hc[5] / 67108864 * v1 * v3)) / 65536
        return v4 * (1 - hc[0] * v4 / 524288)


class LowDriver(I2CMixin, PollMixin, Agent):
    """ Low driver for the BME280. """

    def __init__(self, *args, **kwargs):
        self.collect_task = None
        super().__init__(*args, **kwargs)

        self.output_topic("calibration", r"struct\/32s",
                          "Raw calibration data")
        self.output_topic("output", r"struct\/8s", "Raw measurement")

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

        self.output(self.i2c.read_register(0xf7, amount=8))


class HighDriver(Agent, BME280Calculator):
    """ High driver for the BME280. """

    def __init__(self, *args, **kwargs):
        self.hc, self.pc, self.tc = None, None, None
        self.cached_measurement = None
        super().__init__(*args, **kwargs)
        self.input_topic("calibration", r"struct\/32s",
                         "Raw calibration data", cb=self.on_calibration)
        self.input_topic("input", r"struct\/8s", "Raw measurement")
        self.output_topic("temperature", r"struct\/!f", "Temperature in °C")
        self.output_topic("pressure", r"struct\/!I", "Air pressure in Pascal")
        self.output_topic("humidity", r"struct\/B", "Air humidity in percent")

        self.update_agent(arm=True)

    def on_calibration(self, data):
        """ Receive calibration. """

        self.tc = struct.unpack("<Hhh", data[0:6])
        self.pc = struct.unpack("<Hhhhhhhhh", data[6:24])
        self.hc = list(data[12:18])
        self.hc[4] = (self.hc[4] << 4) | self.hc[5] & 0x0f
        self.hc[5] = (self.hc[5] << 4) | (self.hc[5] >> 4) & 0x0f
        self.hc = tuple(self.hc)

        if self.cached_measurement is not None:
            cm = self.cached_measurement
            self.cached_measurement = None
            self.on_input(cm)

    def on_input(self, data):
        """ Convert incoming measurements to usable data. """

        p_reading = ((data[0] << 16) | (data[1] << 8) | data[2]) >> 4
        t_reading = ((data[3] << 16) | (data[4] << 8) | data[5]) >> 4
        h_reading = (data[6] << 8) | data[7]

        t_fine = self.calc_t_fine(t_reading, self.tc)
        self.temperature(self.calc_temperature(t_fine))
        self.pressure(int(self.calc_pressure(p_reading, t_fine, self.pc)))
        self.humidity(int(self.calc_humidity(h_reading, t_fine, self.hc)))
