""" Test generic module. """

import unittest

import json
import struct
import enum
from mauzr.serializer.base import SerializationError
from mauzr.serializer.generic import String, Struct, JSON, IntEnum, Eval

__author__ = "Alexander Sowitzki"

class StructTest(unittest.TestCase):
    """ Test Struct serializer. """

    def test_all(self):
        """ Test all struct functions. """

        sub_fmt = "!HH"
        fmt = f"struct/{sub_fmt}"
        desc = "TestDescription"

        ser = Struct(sub_fmt, desc)
        self.assertEqual(sub_fmt, ser.struct_fmt)
        self.assertEqual(fmt, ser.fmt)

        self.assertRaises(ValueError, Struct, "!", desc)
        self.assertRaises(ValueError, Struct, "ü", desc)

        self.assertTrue(Struct("!H", desc).simple_type)
        self.assertTrue(Struct("H", desc).simple_type)
        self.assertFalse(Struct("!HH", desc).simple_type)
        self.assertFalse(Struct("HH", desc).simple_type)

        data = (2, 5)
        self.assertEqual(struct.pack("!HH", *data),
                         Struct("!HH", desc).pack(data))
        self.assertEqual(struct.pack("!H", 4), Struct("!H", desc).pack(4))
        self.assertRaises(SerializationError, Struct("!H", desc).pack, (4,))
        self.assertRaises(SerializationError, Struct("!H", desc).pack, data)
        self.assertRaises(SerializationError, Struct("!H", desc).pack, "Test")

        data = bytes([1, 2, 3, 4])
        self.assertEqual(struct.unpack("!HH", data),
                         Struct("!HH", desc).unpack(data))
        data = bytes([1, 2])
        self.assertEqual(struct.unpack("!H", data)[0],
                         Struct("!H", desc).unpack(data))
        self.assertRaises(SerializationError,
                          Struct("!HH", desc).unpack, data)
        self.assertRaises(SerializationError,
                          Struct("!H", desc).unpack, "Test")


        self.assertRaises(ValueError, Struct.from_fmt, "str", desc)
        self.assertRaises(ValueError, Struct.from_fmt, None, desc)
        self.assertRaises(ValueError, Struct.from_fmt, "struct/", desc)
        self.assertRaises(ValueError, Struct.from_fmt, "struct/!", desc)

        ser2 = Struct.from_fmt(fmt, desc)
        self.assertEqual(desc, ser2.desc)
        self.assertEqual(fmt, ser2.fmt)


class StringTest(unittest.TestCase):
    """ Test String serializer. """

    def test_all(self):
        """ Test all functions. """

        s = "Test"
        self.assertEqual("str", String.fmt)
        self.assertEqual(s.encode(), String.pack(s))
        self.assertEqual(s, String.unpack(s.encode()))
        self.assertRaises(SerializationError, String.pack, 3)
        String.pack(None)


class IntEnumTest(unittest.TestCase):
    """ Test String serializer. """

    def test_all(self):
        """ Test all functions. """

        class _E(enum.IntEnum):
            V_A = 1
            V_B = 2
        desc = "SomeDesc"

        ser = IntEnum(enum_cls=_E, enum_fmt="B", desc=desc)

        self.assertEqual(bytes([1]), ser.pack(_E.V_A))
        self.assertEqual(bytes([1]), ser.pack(1))
        self.assertEqual(_E.V_A, ser.unpack(bytes([1])))

        self.assertRaises(SerializationError, ser.unpack, bytes([5]))
        self.assertRaises(SerializationError, ser.pack, 3)


        self.assertEqual(bytes([1]), ser.pack(_E.V_A))

        s = "Test"
        self.assertEqual("str", String.fmt)
        self.assertEqual(s.encode(), String.pack(s))
        self.assertEqual(s, String.unpack(s.encode()))
        self.assertRaises(SerializationError, String.pack, 3)
        String.pack(None)


class JSONTest(unittest.TestCase):
    """ Test JSON serializer. """

    def test_all(self):
        """ Test all functions. """

        ju = {"3": "a", "4": [1, 2, 5]}
        jp = json.dumps(ju).encode()
        self.assertEqual("json", JSON.fmt)
        self.assertEqual(jp, JSON.pack(ju))
        self.assertEqual(ju, JSON.unpack(jp))
        JSON.pack(None)
        self.assertRaises(SerializationError, JSON.unpack,
                          bytes([1, 2, 3, 4]))
        self.assertRaises(SerializationError, JSON.unpack, "{]".encode())


class EvalTest(unittest.TestCase):
    """ Test JSON serializer. """

    def test_all(self):
        """ Test all functions. """

        fct_str = "lambda x: x+3"
        fct = Eval.unpack(fct_str.encode())
        self.assertTrue(callable(fct))
        self.assertEqual(7, fct(4))
        Eval.pack(None)
