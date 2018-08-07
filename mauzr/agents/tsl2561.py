""" Driver for TSL2561 devices. """

from contextlib import contextmanager
from mauzr import Agent, PollMixin, I2CMixin

__author__ = "Alexander Sowitzki"


VALUE_LUT = ((0, 0, 0), (0x40, 0x01f2, 0x01be), (0x80, 0x214, 0x2d1),
             (0xc0, 0x23f, 0x37b), (0x0100, 0x270, 0x3fe),
             (0x0138, 0x16f, 0x1fc), (0x019a, 0xd2, 0xfb), (0x29a, 0x18, 0x12))
""" Lookup table to convert measurement to illumination value. """


class LowDriver(Agent, I2CMixin, PollMixin):
    """ Low level driver to communicate with TSL2561 chips.

    This driver periodically requests measurements from the chip and sends them
    to the high level driver.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.output_topic("output",
                          r"struct\/<HH", "Output for measurements")

        self.collect_task = self._sched.after(self.collect, 5)

    @contextmanager
    def setup(self):
        """ Set up the chip. """

        self.on(True)  # Turn chip on for configuration.
        self.i2c.write([0x81, 2])  # Reset gain setting to be sure.
        self.on(False)  # Chip off.

        yield

        self.collect_task.disable()  # Disable collection task after agent off.

    def poll(self):
        """ Starts the measurement. """

        self.on(True)  # Measurement on.
        self.collect_task.enable()  # Schedule collection.

    def collect(self):
        """ Collect the measurement from the chip and publish it. """

        measurement = self.i2c.read_register(0xac, fmt="<HH")  # Read value.
        self.on(False)  # Stop measuring.
        self.mearement(measurement)  # Publish.

    def on(self, value):
        """ Turn the chips measuring function on or off.

        Args:
            value (bool): If True chip is set to measure, otherwise not.
        """

        self.i2c.write([0x80, 3 if value else 0])


class HighDriver(Agent):
    """ High level driver for TSL2561.

    Receives measurements from the chip and converts them to an
    illuminance reading.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.input_topic("input", r"struct\/<HH", "Raw measurement")
        self.output_topic("output", r"struct\/!f", "Illuminance in lux")

    def on_input(self, channels):
        """ Convert the measurement and publish illuminance.

        Args:
            channels (tuple): Tuple containing readout of the two measurement \
                              channels of the TSL2561.
        """

        if channels[0] > 65000 or channels[1] > 65000:
            # Sensor is oversaturated. Publish infinity.
            # What is the real saturation point?
            self.log.warning("Sensor oversaturated. Publishing infinity")
            self.output(float("inf"))
            return

        channels = (channels[0] * 16, channels[1] * 16)  # Prepare channels

        # Look up constants.
        ratio = 0 if not channels[0] else int(channels[1] * 1024 / channels[0])
        ratio = (ratio + 1) >> 1
        for tres, a, b in VALUE_LUT:
            if ratio <= tres:
                f = (a, b)
                break

        # Do actual calculation.
        channels = [ch * fi for ch, fi in zip(channels, f)]
        illuminance = (max(0, channels[0] - channels[1]) + 8192) >> 14

        self.output(illuminance)
