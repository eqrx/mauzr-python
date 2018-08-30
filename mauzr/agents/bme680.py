""" Driver for BME680 devices. """

import time
import struct

from contextlib import contextmanager
from mauzr import Agent, I2CMixin, PollMixin
from mauzr.serializer import Struct

__author__ = "Alexander Sowitzki"

class BME680Calculator:
    """ Calculation methods for BME680. """

    LUT_A = (2147483647, 2147483647, 2147483647, 2147483647, 2147483647,
             2126008810, 2147483647, 2130303777, 2147483647, 2147483647,
             2143188679, 2136746228, 2147483647, 2126008810, 2147483647,
             2147483647)

    LUT_B = (4096000000, 2048000000, 1024000000, 512000000, 255744255,
             127110228, 64000000, 32258064, 16016016, 8000000, 4000000,
             2000000, 1000000, 500000, 250000, 125000)


    @staticmethod
    def calc_t_fine(reading, tc):
        """ Calculate t_fine.

        Args:
            reading (int): Temperature reading.
            tc (tuple): Temperature calibrations.
        Returns:
            int: Calculated t_fine.
        """

        var1 = (reading >> 3) - (tc[0] << 1)
        var2 = pow(var1 / 2, 2) / 4096 * tc[2] * 16 / 16384
        return int(var1 * tc[1] / 2048 + var2)

    @staticmethod
    def calc_temperature(t_fine):
        """ Calculate temperature.

        Args:
            t_fine (int): T_fine value.
        Returns:
            float: Calculated temperature.
        """

        return (t_fine * 5 + 128) / 25600

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

        var1 = t_fine / 2 - 64000
        var2 = pow(var1 / 4, 2) * pc[5] / 8192 + var1 * pc[4] * 2
        var2 = var2 / 4 + pc[3] * 65536
        var1 = pow(var1 / 4, 2) / 8192
        var1 = var1 * pc[2] / 65536 + pc[1] * var1 / 524288
        var1 = (32768 + var1) * pc[0] / 32768
        pres = (1048576 - reading - var2 / 4096) / var1 * 6250
        var1 = pc[8] * pres * pres / 2147483648
        var2 = pres * pc[7] / 32768 + (pres / 256) ** 3 * pc[9] / 131072
        return pres + (var1 + var2 + pc[6] * 128) / 16

    @classmethod
    def calc_gas_resistance(cls, reading, gas_range, sw_error):
        """ Calculate the gas resistance of the sensor.

        Args:
            cls (class): Owning class.
            reading (int): Resistance reading.
            gas_range (int): Expected range.
            sw_error (int): Calculated error.
        Returns:
            int: Calculated resistance.
        """

        var1 = (1340 + 5 * sw_error) * cls.LUT_A[gas_range] / 65536
        var2 = reading * 32768 - 16777216 + var1
        return int((cls.LUT_B[gas_range] * var1 / 512 + var2 / 2) / var2)

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

        temp_scaled = (t_fine * 5 + 128) / 256
        var1 = (reading - hc[0] * 16) - temp_scaled * hc[2] / 200
        var2 = hc[1] * temp_scaled * hc[3] / 102400 + hc[1] * 16
        var2 += hc[1] * temp_scaled * temp_scaled * hc[4] / 655360000
        var3 = var1 * var2
        var4 = hc[5] * 8 + temp_scaled * hc[6] / 1600
        var5 = var3 * var3 / 274877906944
        calc_hum = (var3 + var4 * var5 / 2) / 4194304

        return calc_hum


class LowDriver(I2CMixin, PollMixin, Agent):
    """ Low driver for the BME680. """

    def __init__(self, *args, **kwargs):
        self.collect_task = None
        super().__init__(*args, **kwargs)

        self.output_topic("calibration", r"struct\/42s",
                          "Raw calibration data")
        self.output_topic("output", r"struct\/15s", "Raw measurement")

        self.update_agent(arm=True)

    @contextmanager
    def setup(self):
        self.collect_task = self.after(1, self.collect)


        self.i2c.write([0xe0, 0xB6])
        time.sleep(0.005)
        data = [self.i2c.read_register(ad, amount=am) for ad, am
                in ((0x89, 25), (0xe1, 16), (0x04, 1))]
        self.calibration(data[0]+data[1]+data[2])
        self.i2c.write([0x5a, 0x73, 0x64, 0x65])
        yield
        self.collect_task = None

    def poll(self):
        """ Start the measurement and the collection task. """

        self.i2c.write([0x74, (0b100 << 5)|(0b011 << 2)])
        self.i2c.write([0x75, 0b010 << 2])
        self.i2c.write([0x71, 0x10])
        self.i2c.write([0x72, 0b010])
        state = (self.i2c.read_register(0x74, amount=1)[0] & 0xFC) | 0x01
        self.i2c.write([0x74, state])

        self.collect_task.enable()

    def collect(self):
        """ Collect the measurement and send it to the high driver. """

        data = self.i2c.read_register(0x1d, amount=15)
        assert data[0] & 0x80 != 0

        self.output(data)

class HighDriver(Agent, BME680Calculator):
    """ High driver for the BME680. """

    def __init__(self, *args, **kwargs):
        self.hc, self.pc, self.tc = None, None, None
        self.gc, self.sw = None, None
        self.cached_measurement = None
        super().__init__(*args, **kwargs)
        self.input_topic("calibration", r"struct\/42s",
                         "Raw calibration data", cb=self.on_calibration)
        self.input_topic("input", r"struct\/15s", "Raw measurement")

        self.output_topic("temperature", r"struct\/!f", "Temperature in °C")
        self.output_topic("pressure", r"struct\/!I", "Air pressure in Pascal")
        self.output_topic("humidity", r"struct\/B", "Air humidity in percent")
        self.output_topic("gas_resistance", r"struct\/!I",
                          "Resistance of the gas sensor")

        self.update_agent(arm=True)

    def on_calibration(self, data):
        """ Receive calibration. """

        data = struct.unpack('<hbBHhbBhhbbHhhBBBHbbbBbHhbb', data[1:39])

        self.tc = [data[x] for x in [23, 0, 1]]
        self.pc = [data[x] for x in [3, 4, 5, 7, 8, 10, 9, 12, 13, 14]]
        self.hc = [data[x] for x in [17, 16, 18, 19, 20, 21, 22]]
        self.gc = [data[x] for x in [25, 24, 26]]

        self.hc[1] = (self.hc[1] << 4) + (self.hc[0] & 0x0f)
        self.hc[0] >>= 4
        self.sw = (data[-1] & 0xf0) >> 4

        if self.cached_measurement is not None:
            cm = self.cached_measurement
            self.cached_measurement = None
            self.on_input(cm)

    def on_input(self, data):
        """ Convert incoming measurements to usable data. """

        def unpack24(data, result=0):
            for b in data:
                result <<= 8
                result += b & 0xff
            return result >> 4

        pressure = unpack24(data[2:5])
        temperature = unpack24(data[5:8])
        humidity = struct.unpack('>H', data[8:10])[0]
        gas = int(struct.unpack('>H', data[13:15])[0] >> 6)
        gas_range = data[14] & 0x0f

        t_fine = BME680Calculator.calc_t_fine(temperature, self.tc)
        self.humidity(int(self.calc_humidity(humidity, t_fine, self.hc)))
        self.pressure(int(self.calc_pressure(pressure, t_fine, self.pc)))
        self.temperature(self.calc_temperature(t_fine))
        gas = self.calc_gas_resistance(gas, gas_range, self.sw)
        self.gas_resistance(int(gas))
