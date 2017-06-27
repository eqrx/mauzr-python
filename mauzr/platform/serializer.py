""" Serializers for data channels. """
__author__ = "Alexander Sowitzki"

import struct

class Enum:
    """ Serialize messages represented by an :class:`enum.Enum`.

    :param enum: The enum to serialize.
    :type enum: enum.Enum
    :param fmt: The format passed to :func:`struct.pack` to serialize the
                enum value.
    :type fmt: str
    """

    def __init__(self, enum, fmt):
        self.enum = enum
        self.fmt = fmt

    def pack(self, enum):
        """ Serialize a given enum to its binary representation.

        :param enum: The enum to serialize.
        :type enum: object
        :returns: The serialized bytes.
        :rtype: bytes
        """
        return struct.pack(self.fmt, enum.value)

    def unpack(self, data):
        """ Deserialize a binary representation into the configured enum.

        :param data: The binary data to deserialize.
        :type data: bytes
        :returns: The deserialized enum.
        :rtype: enum.enum
        """

        return self.enum(struct.unpack(self.fmt, data)[0])

    def __eq__(self, other):
        # Check if enum and fmt are the same
        if isinstance(other, self.__class__):
            return self.enum == other.enum and self.fmt == other.fmt
        return False

class Struct:
    """ Serialize values using :mod:`struct`

    :param fmt: Format to use for :mod:`struct`.
    :type fmt: str
    """

    def __init__(self, fmt):
        self.fmt = fmt

    def pack(self, value):
        """ Serialize a given value to binary representation.

        :param value: The value to serialize. If the value is :class:`tuple` or
                      :class:`list` it will be expanded as arguments for
                      :func:`struct.pack`. Else the value will be passed as
                      first argument.
        :type value: object
        :returns: The serialized bytes.
        :rtype: bytes
        """

        if isinstance(value, (list, tuple)):
            return struct.pack(self.fmt, *value)
        return struct.pack(self.fmt, value)

    def unpack(self, data):
        """ Deserialize a binary representation into the object.

        :param data: The binary data to deserialize.
        :type data: bytes
        :returns: The deserialized object. If multiple fields are specified in
                  the format string the return value of :class:`struct.unpack`
                  if passed. Else the object if returned as in
                  struct.unpack(...)[0]
        :rtype: object
        """

        values = struct.unpack(self.fmt, data)
        return values[0] if len(values) == 1 else values

    def __repr__(self):
        return "<{}{}(\"{}\")>".format(self.__class__.__module__,
                                       self.__class__.__name__, self.fmt)

    def __eq__(self, other):
        # Check if fmt corresponds
        if isinstance(other, self.__class__):
            return self.fmt == other.fmt
        return False

class JSON:
    """ Serialize values using :mod:`json`. """

    @staticmethod
    def pack(value):
        """ Serialize a given object to its binary representation.

        :param value: The object to serialize.
        :type value: object
        :returns: The serialized bytes.
        :rtype: bytes
        """

        import json
        return json.dumps(value)

    @staticmethod
    def unpack(data):
        """ Deserialize a binary representation into a object.

        :param data: The binary data to deserialize.
        :type data: bytes
        :returns: The deserialized object.
        :rtype: object
        """

        import json
        return json.loads(data)

class String:
    """ Serialize values as strings :mod:`struct`. """

    @staticmethod
    def pack(value):
        """
        :param value: Value to pack.
        :type value: object
        :returns: Packed object.
        :rtype: str
        """

        return value.encode()

    @staticmethod
    def unpack(value):
        """
        :param value: Value to unpack.
        :type value: bytes
        :returns: Unpacked Value.
        :rtype: str
        """

        if not isinstance(value, str):
            value = value.decode()

        return value

# pylint: disable = invalid-name
Bool = Struct("?")
