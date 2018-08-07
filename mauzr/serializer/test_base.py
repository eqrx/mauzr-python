""" Test base module. """

import unittest

from . import Serializer, String, JSON, Struct

__author__ = "Alexander Sowitzki"

class SerializerTest(unittest.TestCase):
    """ Test serializer class. """

    def test_well_known(self):
        """ Test well known lookup. """

        desc = "SomeDesc"
        self.assertIsInstance(Serializer.from_well_known(shell=None,
                                                         fmt="str", desc=desc),
                              String)
        self.assertIsInstance(Serializer.from_well_known(shell=None,
                                                         fmt="json", desc=desc),
                              JSON)
        self.assertIsInstance(Serializer.from_well_known(shell=None,
                                                         fmt="struct/!ff",
                                                         desc=desc),
                              Struct)
        self.assertRaises(ValueError,
                          Serializer.from_well_known,
                          shell=None, fmt="eval", desc=desc)

        fmt = "str"
        ser = Serializer.from_well_known(shell=None, fmt=fmt, desc=desc)
        self.assertEqual(fmt, ser.fmt)
        self.assertEqual(desc, ser.desc)

    def test_all(self):
        """ Test all Serializer functions. """

        desc = "TestDescription"
        desc2 = "DifferentDescription"
        fmt = "struct/!H"
        fmt2 = "str"

        class _TestSerializer(Serializer):
            pass
        _TestSerializer.fmt = fmt


        ser = _TestSerializer(shell=None, desc=desc)
        ser.fmt = fmt
        self.assertEqual(desc, ser.desc)
        self.assertEqual(fmt.encode(), ser.fmt_payload)
        self.assertEqual(desc.encode(), ser.desc_payload)
        self.assertNotEqual(None, ser)
        self.assertNotEqual([], ser)
        self.assertEqual(ser, ser)

        ser2 = _TestSerializer(shell=None, desc=desc2)
        ser2.fmt = fmt
        self.assertEqual(ser, ser2)

        ser2 = _TestSerializer(shell=None, desc=desc)
        ser2.fmt = fmt2
        self.assertNotEqual(ser, ser2)

        ser2 = _TestSerializer(shell=None, desc=desc2)
        ser2.fmt = fmt2
        self.assertNotEqual(ser, ser2)

        self.assertRaises(ValueError, Serializer, shell=None, desc=None)
        self.assertRaises(ValueError, _TestSerializer, shell=None, desc=[])

        self.assertRaises(ValueError, _TestSerializer.from_fmt, shell=None,
                          fmt=fmt2, desc=desc)
        self.assertRaises(ValueError, _TestSerializer.from_fmt, shell=None,
                          fmt=fmt2, desc=desc2)

        ser2 = _TestSerializer.from_fmt(shell=None, fmt=fmt, desc=desc2)
        self.assertEqual(desc2, ser2.desc)
        self.assertEqual(fmt, ser2.fmt)
