""" Serializers for opencv. """

# pragma: no cover

import numpy  # pylint: disable=import-error
import cv2  # pylint: disable=import-error

from .base import Serializer

__author__ = "Alexander Sowitzki"


class Image(Serializer):  # pragma: no cover
    """ Image serializer using openCV.

    Args:
        desc (str): Descriptions of the images.
        encoding (int): Flags to pass to cv2.imdecode. \
                        Defaults to cv2.IMREAD_UNCHANGED.
        shape (tuple): Shape (Width, Height) to enforce for the image. \
                       May be None, which means all shapes are accepted.
    """

    fmt = "image"

    def __init__(self, desc, encoding=cv2.IMREAD_UNCHANGED, shape=None):
        super().__init__(desc)
        self._encoding = encoding
        self._shape = shape

    def pack(self, image):
        """ Pack an image.

        Args:
            image (numpy.ndarray): Image to pack.
        Returns:
            bytes: Packed image.
        Raises:
            ValueError: If image has invalid shape.
        """

        expected, actual = self._shape, image.shape

        if expected and actual != expected:
            raise ValueError(f"Expected img shape {expected} but got {actual}.")
        return image.tobytes()

    def unpack(self, data):
        """ Unpack an image.

        Args:
            data (bytes): Image as bytes.
        Return:
            numpy.ndarray: Deserialized image.
        Raises:
            ValueError: If image has invalid shape.
        """

        data = numpy.fromstring(data, numpy.uint8)
        image = cv2.imdecode(data, self._encoding)
        expected, actual = self._shape, image.shape

        if expected and actual != expected:
            raise ValueError(f"Expected img shape {expected} but got {actual}.")
        return image
