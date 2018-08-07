""" Generic serializers. """

import struct
import json

from .base import Serializer, SerializationError

__author__ = "Alexander Sowitzki"

class String(Serializer):
    """ String serializer.

    Args:
        desc (str): Description of handled string.
    """

    fmt = "str"

    @staticmethod
    def pack(string):
        """ Pack string into bytes.

        Args:
            string (str): String to pack.
        Returns:
            bytes: Packed string.
        Raises:
            SerializationError: On error.
        """

        if string is None:
            return bytes()
        if not isinstance(string, str):
            raise SerializationError(f"Not a string: {string}")

        return string.encode()

    @staticmethod
    def unpack(data):
        """ Unpack string.

        Args:
            data (bytes): String encoded as bytes.
        Returns:
            str: Unpacked string.
        """

        return data.decode()


class Bytes(Serializer):
    """ Serializer for an arbitrary amount of bytes.

    Args:
        desc (str): Description of handled string.
    """

    fmt = None

    @staticmethod
    def pack(data):
        """ Pack bytes.

        Args:
            data (bytes): Bytes or list of ints to pack.
        Returns:
            bytes: Same bytes, new object.
        Raises:
            SerializationError: On error.
        """

        if data is None:
            return bytes()

        try:
            return bytes(data)
        except ValueError as err:
            raise SerializationError(err)


    @staticmethod
    def unpack(data):
        """ Unpack bytes.

        Args:
            data (bytes): Bytes to unpack
        Returns:
            str: Same bytes, new object.
        Raises:
            SerializationError: On error.
        """

        try:
            return bytes(data)
        except ValueError as err:
            raise SerializationError(err)


class Struct(Serializer):
    """ Serializer using struct module.

    Args:
        shell (mauzr.shell.Shell): Shell to use.
        fmt (str): Format used for struct module.
        desc (str): Description of handled information.
    """

    fmt = "struct/" # Default format without struct format.

    def __init__(self, shell, fmt, desc):
        super().__init__(shell=shell, desc=desc)
        if struct.calcsize(fmt) == 0:
            raise ValueError(f"Invalid format: {fmt}")

        self.fmt = "struct/{}".format(fmt)  # Concat serializer and struct info.
        self.struct_fmt = fmt
        # Serializer handles simple type if format contains only one field.
        self.simple_type = len(fmt) == 1 or len(fmt) == 2 and fmt[0] in "!<>"

    def pack(self, obj):
        """ Pack field into bytes.

        Args:
            obj (object): Single field if simple type or \
                          tuple of fields to pack.
        Returns:
            bytes: Packed bytes.
        Raises:
            SerializationError: When packing failes.
        """

        try:
            if self.simple_type:
                return struct.pack(self.struct_fmt, obj)
            return struct.pack(self.struct_fmt, *obj)
        except struct.error as err:
            raise SerializationError(err)

    def unpack(self, data):
        """ Unpack bytes into fields.

        Args:
            data (bytes): Packed fields.
        Returns:
            object: Single field if simple type or list of fields.
        Raises:
            SerializationError: When packing failes.
        """

        try:
            obj = struct.unpack(self.struct_fmt, data)
        except (struct.error, TypeError) as err:
            raise SerializationError(err)
        return obj[0] if self.simple_type else obj

    @classmethod
    def from_fmt(cls, shell, fmt, desc=None):
        """ Instantiate struct serializer from format.

        Args:
            shell (mauzr.shell.Shell): Shell to use.
            fmt (str): Format ("struct/" with field suffix) to create from.
            desc (str): Description of information to handle. May be None.
        Returns:
            Struct: New serializer.
        Raises:
            ValueError: When fmt is invalid.
        """

        if not isinstance(fmt, str) or not fmt.startswith(cls.fmt):
            raise ValueError(f"Invalid format: {fmt}")
        return cls(shell=shell, fmt=fmt.split("/")[1], desc=desc)


class JSON(Serializer):
    """ JSON serializer. """

    fmt = "json"

    @staticmethod
    def pack(obj):
        """ Pack complex data structure into JSON string.

        Args:
            obj (object): Complex data structure.
        Returns:
            bytes: JSON string.
        """
        return json.dumps(obj).encode()

    @staticmethod
    def unpack(data):
        """ Unpacks JSON string into data structure.

        Args:
            data (bytes): JSON string.
        Returns:
            object: Complex data structure.
        Raises:
            SerializationError: On error.
        """

        try:
            return json.loads(data.decode())
        except json.JSONDecodeError as err:
            raise SerializationError(err)


class IntEnum(Struct):
    """ Serialize enum.IntEnum using the struct module.

    Args:
        shell (mauzr.shell.Shell): Shell to use.
        enum_cls (enum.IntEnum): The enum to serialize.
        enum_fmt (str): Format given to struct module to pack the enum value.
        desc (str): Description of handled enum.
    """

    fmt = None

    def __init__(self, shell, enum_cls, enum_fmt, desc):
        super().__init__(shell=shell, fmt=enum_fmt, desc=desc)
        self.enum_cls = enum_cls

    def pack(self, enm):
        """ Pack enum into bytes.

        Args:
            enm (enum.IntEnum): Enum instance.
        Returns:
            bytes: Packed enum.
        Raises:
            SerializationError: On error.
        """

        if isinstance(enm, self.enum_cls):
            value = enm.value
        else:
            try:
                self.enum_cls(enm)
            except ValueError:
                raise SerializationError(f"Not an enum key: {enm}")
            value = enm

        return super().pack(value)

    def unpack(self, data):
        """ Unpack bytes into enum.

        Args:
            data (bytes): Enum as bytes.
        Returns:
            enum.IntEnum: Enum instance.
        Raises:
            SerializationError: On error.
        """

        obj = super().unpack(data)
        try:
            return self.enum_cls(obj)
        except ValueError:
            raise SerializationError(f"Not an enum key: {obj}")


class Eval(String):
    """ Deserializer that uses eval to unpack string data. """
    fmt = None

    @staticmethod
    def unpack(data):
        """ Unpack bytes into string and call eval with it. Return result.

        Args:
            data(bytes): Packed string.
        Returns:
            object: Return value of eval.
        Raises:
            SerializationError: On error.
        """

        try:
            # pylint: disable=eval-used
            return eval(String.unpack(data))
        except SyntaxError:
            raise SerializationError(f"Invalid statement: {data}")
