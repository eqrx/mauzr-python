"""
.. module:: mauzr.hardware.ws2812.controller
   :platform: all
   :synopsis: Controller for ws2812 chains.

.. moduleauthor:: Alexander Sowitzki <dev@eqrx.net>
"""

import math

class Compositor:
    """ Helper to composite pixel colors.

    :param pixels: Pixel coordinates to manage.
    :type pixels: tuple
    """

    def __init__(self, pixels):
        self.pixels = pixels

    @staticmethod
    def normalize(value):
        """ Crop a given value to be between 0.0 and 1.0.

        :param value: Value to crop.
        :type value: int
        :returns: Croped value.
        :rtype: int
        """

        return min(max(value, 0.0), 1.0)

    def _channel(self, pixel, channel):
        """ Return the color a a pixel channel. """

        raise NotImplementedError()

    def color(self, pixel):
        """ Return the color of a single pixel.

        :param pixel: Pixel coordinates.
        :type pixel: collections.abc.Iterable
        :returns: Color of the pixel als RGB tuple.
        :rtype: tuple
        """

        return [self._channel(pixel, channel) for channel in range(0, 3)]

    def colors(self):
        """ Return the colors of all pixels.

        :returns: Colors of all pixels as list.
        :rtype: list
        """

        return [self.color(pixel) for pixel in self.pixels]

    @staticmethod
    def distance(a, b):
        """ Get distance detween two points. """

        return math.sqrt(sum([pow(ai-bi, 2) for ai, bi in zip(a, b)]))

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
