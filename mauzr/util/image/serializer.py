""" Serializer for images. """
__author__ = "Alexander Sowitzki"

import io
import PIL.Image # pylint: disable=import-error

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

        stream = io.BytesIO(data)
        return PIL.Image.open(stream)
