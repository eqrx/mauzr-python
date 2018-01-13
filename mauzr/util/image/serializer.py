""" Serializer for images. """

import io

__author__ = "Alexander Sowitzki"


class OpenCV:
    """ Serialize images with openCV. """

    @staticmethod
    def pack(image):
        """
        :param image: Image to pack.
        :type image: numpy.ndarray
        :returns: Packed image.
        :rtype: bytes
        """

        return image.tostring()

    @staticmethod
    def unpack(data):
        """
        :param data: Packed image.
        :type data: bytes
        :returns: Unpacked image.
        :rtype: PIL.Image
        """

        import cv2  # pylint: disable=import-error
        import numpy  # pylint: disable=import-error

        data = numpy.fromstring(data, numpy.uint8)
        return cv2.imdecode(data, cv2.IMREAD_UNCHANGED)


class Pillow:
    """ Serialize images with pillow.

    :param fmt: Image format. See :class:`PIL.Image.Image`
    :type fmt: str
    """

    def __init__(self, fmt):
        self._format = fmt

    def pack(self, image):
        """
        :param image: Image to pack.
        :type image: PIL.Image.Image
        :returns: Packed image.
        :rtype: bytes
        """

        stream = io.BytesIO()
        image.save(stream, format=self._format)
        stream.seek(0)
        return bytes(stream.getbuffer())

    @staticmethod
    def unpack(data):
        """
        :param data: Packed image.
        :type data: bytes
        :returns: Unpacked image.
        :rtype: PIL.Image
        """

        import PIL.Image  # pylint: disable=import-error

        return PIL.Image.open(io.BytesIO(data))


class Pygame:
    """ Serialize images for pygame. """

    @staticmethod
    def pack(image):
        """ Pack is not implemented for surfaces. """
        raise NotImplementedError()

    @staticmethod
    def unpack(data):
        """
        :param data: Packed image.
        :type data: bytes
        :returns: Unpacked image.
        :rtype: pygame.Surface
        """

        import pygame  # pylint: disable=import-error

        return pygame.image.load(io.BytesIO(data))
