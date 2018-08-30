""" Driver for ADS1015 devices. """

import enum
from contextlib import contextmanager
from mauzr import Agent, I2CMixin, PollMixin, serializer

__author__ = "Alexander Sowitzki"


class Gain(enum.IntFlag):
    """ ADC gain setting. """

    TWO_THIRD = 0x00
    ONE = 0x02
    TWO = 0x04
    FOUR = 0x06
    EIGHT = 0x08
    SIXTEEN = 0x0a


class LowDriver(I2CMixin, PollMixin, Agent):
    """ Low driver for the ADS1015. """

    def __init__(self, *args, **kwargs):
        self.collect_task = None
        super().__init__(*args, **kwargs)

        self.output_topic("output", r"struct\/!H", "Measurement")
        self.option("gain", "struct/B", "ADC gain",
                    ser=serializer.IntEnum(self.shell, Gain, "B", "ADC gain"))

        self.update_agent(arm=True)

    @contextmanager
    def setup(self):
        self.collect_task = self.after(1, self.collect)
        yield
        self.collect_task = None

    def poll(self):
        """ Start the measurement and the collection task. """

        channel = 0
        config = (channel+0x04 & 0x07) << 12 | 0x8183 | self.gain << 8
        self.i2c.write([0x01, config >> 8 & 0xFF, config & 0xFF])
        self.collect_task.enable()

    def collect(self):
        """ Collect and publish result. """

        msb, lsb = self.i2c.read_register(0x00, amount=2)
        sample = msb << 4 | lsb >> 4
        if sample & 0x800:
            sample -= 1 << 12
        self.output(sample)
