""" Driver for WS2812 leds. """

import math
import struct
from contextlib import contextmanager, suppress
from mauzr import Agent, PollMixin, Serializer, SPIMixin

__author__ = "Alexander Sowitzki"


class FloatCoordinatesSerializer(Serializer):
    """ Serializer for variable length lists of float XYZ coordinates.

    Args:
        desc (str): Description of the use for the handles coordinates.
    """

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


class LowDriver(SPIMixin, Agent):
    """ Low level driver for WS2812 and similar LED controllers.

    Communication with pixels is done via SPI hardware with the baudrate set
    to 3200000 Hz. This agent receives a byte array and writes it to the pixels.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.input_topic("input", r"struct/\d+s", "Input for raw pixel data")

        self.update_agent(arm=True)

    def on_input(self, values):
        """ Transfer given data to the pixels.

        Args:
            values (bytes): Values to transfer to the pixels.
        Raises:
            OSError: Hardware failure.
        """

        self.spi.transfer(values)

class HighDriver(Agent):
    """ Receives color states for pixels to convert it for the low level driver.

    Colors are given as a list of color channels (=float array) and are
    converted into an array of bytes.
    """

    def __init__(self, *args, **kwargs):
        self.lut = tuple(self.generate_lut())
        super().__init__(*args, **kwargs)

        self.output_topic("output", r"struct/\d+s", "Output for raw pixel data")
        self.input_topic("input", r"struct\/\d+B", "Input for channel colors")
        self.update_agent(arm=True)

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
                buf |= (0xf8 if i & pow(2, m) else 0xc0) << m*8
            yield struct.pack(">Q", buf)

    def on_input(self, vals):
        """ Convert channel values for low level driver and send it out.

        Args:
            vals (tuple): Tuple containing tuples with channel values \
                          as floats.
        Raises:
            ValueError: Invalid input.
        """
        buf = bytearray()
        for v in vals:
            buf.extend(self.lut[v])
        self.output(buf)


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
        self.enabled = False
        super().__init__(*args, **kwargs)

        self.output_topic("output", r"struct\/\d+B",
                          "Output for channel values")
        ser = FloatCoordinatesSerializer(shell=self.shell,
                                         desc="Compositor coordinates")
        self.option("coordinates", None, "Input for pixel coordinates",
                    ser=ser, cb=self.on_coord_change)

        self.input_topic("enabled", r"struct\/\?", "Compositor enabled",
                         cb=self.on_enabled, restart=False)
        self.update_agent(arm=True)

    def on_enabled(self, enabled):
        """ Enable of disable to compositor

        Args:
            enabled (bool): Enabled bool.
        """

        self.enabled = enabled

    def on_coord_change(self, values):
        """ Called when the coordiante set changed.

        Args:
            values (list): List of new coordinates.
        """

    def poll(self):
        """ Poll current color setting and publish it to output. """

        c = self.colors()
        if c:
            self.output(c)

    def colors(self):
        """ Return colors of all coordinates in the order they were specified.

        Returns:
            list: List containing tuples with color channels as floats within.
        """

        buf = bytearray()
        for coord in self.coords:
            buf.extend(self.color(coord))
        return buf

    def color(self, coord):
        """ Return the color at a coordinate.

        Method may be overridden to increase performance. If overridden
        channel may not be implemented.

        Args:
            coord (tuple): Requested coordinate.
        Returns:
            tuple: Tuple containing channel values as floats.
        """

        return [min(max(self.channel(coord, channel), 0), 255)
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
