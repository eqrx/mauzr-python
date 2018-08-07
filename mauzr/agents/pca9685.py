""" PCA9685 driver. """

from contextlib import contextmanager
from mauzr import Agent, I2CMixin

__author__ = "Alexander Sowitzki"


class LowDriver(Agent, I2CMixin):
    """ Directly interface with a PCA9685 chip via I2C to drive PWMs. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.input_topic("input", r"struct\/!16H",
                         "Setting for the PCA9685 values")

    @contextmanager
    def setup(self):
        self._i2c.write([0x06])  # Reset
        yield
        self._i2c.write([0x06])  # Reset

    def on_input(self, values):
        for i in range(0, 64, 2):
            self._i2c.write(values[i:i+2])


class HighDriver(Agent):
    """ Converts float inputs into something the low level can handle. """

    def __init__(self, *args, **kwargs):
        self._values = [0.0] * 16
        super().__init__(*args, **kwargs)

        self.output_topic("output", r"struct\/!16H", "")
        for i in range(16):
            self.input_topic(f"input_{i}", r"struct\/!f",
                             f"Setting for PWM {i}",
                             sub={"wants_handle": True})

        self.update_agent(arm=True)

    def on_input(self, values):
        data = []
        for channel, v in zip(range(0, 16), self._values):
            v = int(v*4096)
            offset = channel * 4
            data.extend(((0x6+offset, 0), (0x7+offset, 0),
                         (0x8+offset, v & 0xff), (0x9+offset, v >> 8)))
        self.output(data)
