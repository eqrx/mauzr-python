""" Serializer for images. """
__author__ = "Alexander Sowitzki"

import io

class ImageSerializer:
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
        buf = bytes(stream.getbuffer())
        return buf

    @staticmethod
    def unpack(data):
        """
        :param data: Packed image.
        :type data: bytes
        :returns: Unpacked image.
        :rtype: PIL.Image
        """

        import PIL.Image # pylint: disable=import-error

        stream = io.BytesIO(data)
        return PIL.Image.open(stream)

class SurfaceSerializer:
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

        import pygame # pylint: disable=import-error

        stream = io.BytesIO(data)
        return pygame.image.load(stream)
