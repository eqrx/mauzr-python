""" Driver for WS2812 leds. """

import math
import struct
from contextlib import contextmanager
from mauzr import Agent, PollMixin, Serializer

__author__ = "Alexander Sowitzki"


class FloatCoordinatesSerializer(Serializer):
    """ Serializer for variable length lists of float XYZ coordinates.

    Args:
        desc (str): Description of the use for the handles coordinates.
    """

    def __init__(self, desc):
        super().__init__("bytes", desc)

    @staticmethod
    def unpack(data):
        """ Unpack data into coordinates.

        Args:
            data (bytes): Packed coordinates
        Returns:
            list: List of tuples of XYZ float coordinates.
        Raises:
            ValueError: If coordinates are invalid.
        """

        if len(data) % 4:
            raise ValueError("Data length {len(data)} not dividable by four "\
                             " and not convertible into float coordinates.")
        float_count = len(data) // 4
        if float_count % 3:
            raise ValueError("{float_count} coordinates cannot be grouped "\
                             "into XYZ coordinates.")

        coords = struct.unpack(f"!{float_count}f", data)
        return  [coords[i:i+3] for i in range(0, len(coords), 3)]


class LowDriver(Agent):
    """ Low level driver for WS2812 and similar LED controllers.

    Communication with pixels is done via SPI hardware with the baudrate set
    to 3200000 Hz. This agent receives a byte array and writes it to the pixels.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.option("bus_name", "str", "Name of the bus agent")
        self._spi = None

        self.input_topic("input", r"bytes/\d+", "Input for raw pixel data")

    @contextmanager
    def setup(self):
        self._spi = self._shell[self._bus_name]
        yield
        self._spi = None

    def on_input(self, values):
        """ Transfer given data to the pixels.

        Args:
            values (bytes): Values to transfer to the pixels.
        Raises:
            OSError: Hardware failure.
        """

        self._spi.transfer(values)





class HighDriver(Agent):
    """ Receives color states for pixels to convert it for the low level driver.

    Colors are given as a list of color channels (=float array) and are
    converted into an array of bytes.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.option("channel_count", "struct/!H", "Channel count")
        self.output_topic("output", r"bytes\/\d+", "Output for raw pixel data")
        self.input_topic("input", r"struct\/!\d+f", "Input for channel colors")
        self.lut = tuple(self.generate_lut())

    @staticmethod
    def generate_lut():
        """ Generator for the pixel lookup table.

        Each bit inside the color channel is surrounded with a 1 and a 0.
        So each color byte yields three bytes that are send for this channel.

        Yields:
            bytes: Mapped value for the given index value.
        """

        for i in range(0, 256):
            buf = 0
            for m in range(0, 8):
                buf |= (0b110 if i & pow(2, m) else 0b100) << m*3
            yield struct.pack(">I", buf)[1:4]

    def on_input(self, vals):
        """ Convert channel values for low level driver and send it out.

        Args:
            vals (tuple): Tuple containing tuples with channel values \
                          as floats.
        Raises:
            ValueError: Invalid input.
        """

        if len(vals) != self.channel_count:
            raise ValueError("Expected {self.channel_count}, got {len(vals)}")
        self.output([self.lut[int(v*255)] for v in vals])


class Compositor(Agent, PollMixin):
    """ Helper class to color WS2812.

    To ease the creation of complex color setups, this class maps the RGB
    pixels into a coordinate space. When the pixel chain is updates, the
    inheriting classes is asked for the color of a coordinate instead of a
    pixel id.

    This class expects the field _coords to be filled with coordinates where
    the pixels are located an _channels to contain the count of color
    channels per pixel.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.output("output", r"struct\/!\d+f", "Output for channel values")
        self.option("coordinates", None, "Input for pixel coordinates",
                    ser=FloatCoordinatesSerializer)
        self.coords = None

    def poll(self):
        """ Poll current color setting and publish it to output. """

        self.output(self.colors())

    def colors(self):
        """ Return colors of all coordinates in the order they were specified.

        Returns:
            list: List containing tuples with color channels as floats within.
        """

        return [self.color(pixel) for pixel in self.pixels]

    def color(self, coord):
        """ Return the color at a coordinate.

        Method may be overridden to increase performance. If overridden
        channel may not be implemented.

        Args:
            coord (tuple): Requested coordinate.
        Returns:
            tuple: Tuple containing channel values as floats.
        """

        return [min(max(self.channel(coord, channel), 0.0), 1.0)
                for channel in range(self.channels)]

    def channel(self, coord, channel):
        """ Return the intensity for a color channel at a coordinate.

        Args:
            coord (tuple): Requested coordinate.
            channel (int): Channel id.
        Returns:
            float: Intensity of the channel. Must be normalized to be \
            withing 0.0 and 1.0.
        """

        raise NotImplementedError()


def create_ring_coordinates(radius, count):
    """ Create coordinates arranged in a circle.

    Args:
        radius (float): Radius
        count (int): Count of coordinates to generate.
    Returns:
        tuple: Tuple of the coordinates.
    """

    pixelstep = math.radians(360/count)
    pixels = []
    for index in range(0, count):
        pixels.append((radius * math.cos(index*pixelstep),
                       radius * math.sin(index*pixelstep)))
    return pixels
