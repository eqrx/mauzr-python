""" Test serializer module. """

import json

from unittest.mock import Mock, NonCallableMock, call
import unittest
from mauzr.serializer import SerializationError, String, Struct
from mauzr.serializer.topic import Topic, Topics
from mauzr.mqtt.test_handle import MQTTHandleTest
from mauzr.mqtt import Handle

__author__ = "Alexander Sowitzki"

class TopicTest(unittest.TestCase):
    """ Test Topic serializer. """

    def test_all(self):
        """ Test all functions. """

        topic = "a/b/2"
        qos = 0
        retain = False

        self.assertEqual("topic", Topic.fmt)
        dfn = {"topic": topic, "qos": qos, "retain": retain, "fmt": "str"}
        packed = json.dumps(dfn).encode()
        mqtt = Mock(spec_set=[])
        shell = NonCallableMock(spec_set=["mqtt"], mqtt=mqtt)
        ser = Topic(shell=shell, desc="SomeDesc")
        ser.unpack(packed)
        mqtt.assert_called_once_with(topic=dfn["topic"], qos=dfn["qos"],
                                     retain=dfn["retain"],
                                     ser=String(desc=ser.desc))

        self.assertRaises(SerializationError, ser.unpack, "{]".encode())
        self.assertRaises(SerializationError, ser.unpack,
                          bytes([1, 2, 3, 4]))
        ser.pack(None)

        mqtt = MQTTHandleTest.mqtt_mock()
        sched = NonCallableMock(spec_set=[])

        handle = Handle(mqtt=mqtt, sched=sched, topic=topic,
                        ser=String("SomeDesc"), qos=qos,
                        retain=retain)
        self.assertEqual(json.loads(ser.pack(handle).decode()), dfn)

class TopicsTest(unittest.TestCase):
    """ Test Topics serializer. """

    def test_all(self):
        """ Test all functions. """
        # pylint: disable=too-many-locals

        self.assertEqual("topics", Topics.fmt)
        topic1 = "a/b/2"
        topic2 = "a/b/3 "
        qos1 = 1
        qos2 = 2
        retain1 = False
        retain2 = True
        fmt1 = "str"
        sub_fmt = "!HH"
        fmt2 = f"struct/{sub_fmt}"

        dfn = [{"topic": topic1, "qos": qos1, "retain": retain1, "fmt": fmt1},
               {"topic": topic2, "qos": qos2, "retain": retain2, "fmt": fmt2}]
        packed = json.dumps(dfn).encode()
        mqtt = Mock(spec_set=[])
        shell = NonCallableMock(spec_set=["mqtt"], mqtt=mqtt)
        ser = Topics(shell=shell, desc="SomeDesc")
        ser.unpack(packed)
        mqtt.assert_has_calls([call(topic=topic1, qos=qos1, retain=retain1,
                                    ser=String(desc=ser.desc)),
                               call(topic=topic2, qos=qos2, retain=retain2,
                                    ser=Struct(fmt=sub_fmt, desc=ser.desc))])

        self.assertRaises(SerializationError, ser.unpack, "{]".encode())
        self.assertRaises(SerializationError, ser.unpack,
                          bytes([1, 2, 3, 4]))
        ser.pack(None)

        mqtt = MQTTHandleTest.mqtt_mock()
        sched = NonCallableMock(spec_set=[])

        handle1 = Handle(mqtt=mqtt, sched=sched, topic=topic1,
                         ser=String(desc=ser.desc), qos=qos1, retain=retain1)
        handle2 = Handle(mqtt=mqtt, sched=sched, topic=topic2,
                         ser=Struct(fmt=sub_fmt, desc=ser.desc),
                         qos=qos2, retain=retain2)
        self.assertEqual(json.loads(ser.pack((handle1, handle2)).decode()), dfn)
