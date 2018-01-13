""" Controller for ws2812 chains."""

import math
from mauzr.serializer import Struct

__author__ = "Alexander Sowitzki"


class Compositor:
    """ Helper to composite pixel colors.

    :param pixels: Pixel coordinates to manage.
    :type pixels: tuple
    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict
    """

    def __init__(self, core, pixels, cfgbase="compositor", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)
        self._cfg = cfg

        self._mqtt = core.mqtt
        self._pixels = pixels
        serializer = Struct("!" + "fff" * len(pixels))

        if "coordinates_topic" in cfg:
            d = [item for sublist in pixels for item in sublist]
            core.mqtt.setup_publish(cfg["coordinates_topic"], serializer, 0, d)
        core.mqtt.setup_publish(cfg["topic"], serializer, 0)

        core.scheduler(self._update, 1000//cfg["freq"], single=False).enable()

    def color(self, pixel):
        """ Return the color of a single pixel.

        :param pixel: Pixel coordinates.
        :type pixel: collections.abc.Iterable
        :returns: Color of the pixel als RGB tuple.
        :rtype: tuple
        """

        return [min(max(self._channel(pixel, channel), 0.0), 1.0)
                for channel in range(0, 3)]

    def colors(self):
        """ Return the colors of all pixels.

        :returns: Colors of all pixels as list.
        :rtype: list
        """

        return [self.color(pixel) for pixel in self._pixels]

    def _update(self):
        raise NotImplementedError()

    def _channel(self, pixel, channel):
        """ Return the color a a pixel channel. """

        raise NotImplementedError()


def create_ring_coordinates(radius, count):
    """ Create coordinates arranged in a ring.

    :param radius: Radius of the ring.
    :type radius: float
    :param count: Count of coordinates to generate.
    :type count: int
    :returns: Tuple of the coordinates.
    :rtype: tuple
    """

    pixelstep = math.radians(360/count)
    pixels = []
    for index in range(0, count):
        pixels.append((radius * math.cos(index*pixelstep),
                       radius * math.sin(index*pixelstep)))
    return pixels
