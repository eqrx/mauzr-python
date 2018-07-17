""" Serializers for pygame. """

# pragma: no cover

import io
import pygame  # pylint: disable=import-error

__author__ = "Alexander Sowitzki"

from . import Serializer


class PygameSurface(Serializer):  # pragma: no cover
    """ Deserialize an image into an pygame surface. """

    fmt = "image"

    @staticmethod
    def unpack(data):
        """ Unpack image directly into pygame surface.

        Args:
            data (bytes): Packed image.
        Returns:
            pygame.Surface: Unpacked image.
        """

        return pygame.image.load(io.BytesIO(data))
