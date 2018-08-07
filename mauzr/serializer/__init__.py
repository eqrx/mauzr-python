""" Serializers for data channels. """

from contextlib import suppress

# pylint: disable=unused-import
from .base import Serializer, SerializationError
from .generic import Struct, String, JSON, Eval, IntEnum, Bytes
from .topic import Topic, Topics
with suppress(ImportError):
    from .gui import PygameSurface
with suppress(ImportError):
    from .image import Image
    Serializer.WELL_KNOWN.append(Image)
Serializer.WELL_KNOWN.extend((Struct, String, JSON, Topic, Topics))

__author__ = "Alexander Sowitzki"
