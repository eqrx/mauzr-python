""" Agent module test. """

import struct
import logging
import unittest
from unittest.mock import Mock, NonCallableMock, call
from mauzr.mqtt.handle import Handle
from mauzr.serializer import Struct

class MQTTHandleTest(unittest.TestCase):
    """ Test Agent class. """

    @staticmethod
    def mqtt_mock():
        """ Create an MQTT mock. """

        return Mock(spec_set=["subscribed_handles", "handles", "unsubscribe",
                              "publish", "log", "subscribe"],
                    handles={}, subscribed_handles=set(),
                    subscribe=Mock(spec_set=[]),
                    publish=Mock(spec_set=[]), log=logging.getLogger())

    def test_publish(self):
        """ Test publish function. """

        mqtt = self.mqtt_mock()
        sched = NonCallableMock(spec_set=[])
        topic = "SomeTopic"
        retain = True
        qos = 0
        ser = Struct("!ff", "SomeDesc")
        handle = Handle(mqtt=mqtt, sched=sched, topic=topic, ser=ser,
                        qos=qos, retain=retain)
        value = (3.0, 1.7)
        packed = ser.pack(value)
        handle(*value)
        mqtt.publish.assert_called_once_with(handle=handle, payload=packed)
        mqtt.publish.reset_mock()
        handle(value)
        mqtt.publish.assert_called_once_with(handle=handle, payload=packed)
        mqtt.subscribe.assert_not_called()
        mqtt.unsubscribe.assert_not_called()
        mqtt.assert_not_called()

    def test_child(self):
        """ Test child creation. """

        mqtt = self.mqtt_mock()
        sched = NonCallableMock(spec_set=[])
        topic = "a/b/2"
        handle = Handle(mqtt=mqtt, sched=sched, topic=topic,
                        ser=Struct("!ff", "SomeDesc"), qos=0, retain=True)

        sub_topic = "6/3"
        qos = 1
        retain = False
        ser = Struct("!BBB", "OtherDesc")
        sub = handle.child(topic=sub_topic, qos=qos, retain=retain, ser=ser)
        mqtt.assert_called_once_with(topic=f"{topic}/{sub_topic}", qos=qos,
                                     retain=retain, ser=ser)
        self.assertIs(mqtt(), sub)

    def test_connection(self):
        """ Test connection handling. """

        mqtt = self.mqtt_mock()
        sched = NonCallableMock(spec_set=[])
        topic = "SomeTopic"
        struct_fmt = "!ff"
        handle = Handle(mqtt=mqtt, sched=sched, topic=topic, qos=0, retain=True,
                        ser=Struct(struct_fmt, "SomeDesc"))

        cb = Mock(spec_set=[])
        _token = handle.sub(cb)
        mqtt.subscribe.assert_called_once_with(handle=handle)
        sub_id = mqtt.subscribe()
        mqtt.subscribe.reset_mock()
        handle.on_sub(sub_id)
        self.assertTrue(handle.subbed)
        handle.on_connect(new_session=False)
        mqtt.subscribe.assert_not_called()
        self.assertTrue(handle.subbed)
        handle.on_connect(new_session=True)
        mqtt.subscribe.assert_called_once_with(handle=handle)
        self.assertFalse(handle.subbed)
        mqtt.publish.assert_not_called()
        value = (3.0, 3.0)
        packed = struct.pack(struct_fmt, *value)
        handle(value)
        mqtt.publish.assert_called_once_with(handle=handle, payload=packed)
        mqtt.publish.reset_mock()
        handle.on_connect(new_session=True)

    def test_sub_unsub(self):
        """ Test handling of sub & unsub. """

        mqtt = self.mqtt_mock()
        sched = NonCallableMock(spec_set=[])
        topic = "SomeTopic"
        struct_fmt = "!ff"
        handle = Handle(mqtt=mqtt, sched=sched, topic=topic, qos=0, retain=True,
                        ser=Struct(struct_fmt, "SomeDesc"))

        cb = Mock(spec_set=[])
        self.assertIs(handle, mqtt.handles[topic])
        self.assertNotIn(handle, mqtt.subscribed_handles)
        token = handle.sub(cb)
        mqtt.subscribe.assert_called_once_with(handle=handle)
        self.assertIs(handle, mqtt.handles[topic])
        self.assertNotIn(handle, mqtt.subscribed_handles)
        del token
        mqtt.unsubscribe.assert_called_once_with(handle=handle)
        mqtt.unsubscribe.reset_mock()
        mqtt.publish.assert_not_called()
        mqtt.assert_not_called()

        self.assertIs(handle, mqtt.handles[topic])
        self.assertNotIn(handle, mqtt.subscribed_handles)
        cb = Mock(spec_set=[])
        token = handle.sub(cb)
        self.assertNotIn(handle, mqtt.subscribed_handles)
        handle.on_sub(mqtt.subscribe())
        self.assertIn(handle, mqtt.subscribed_handles)
        mqtt.unsubscribe.assert_not_called()
        del token
        self.assertIn(handle, mqtt.subscribed_handles)
        mqtt.unsubscribe.assert_called_once_with(handle=handle)
        handle.on_unsub(mqtt.unsubscribe())
        mqtt.unsubscribe.reset_mock()
        self.assertIs(handle, mqtt.handles[topic])
        self.assertNotIn(handle, mqtt.subscribed_handles)
        mqtt.unsubscribe.assert_not_called()

    def test_incoming_publish(self):
        """ Test incoming publish handling. """

        mqtt = self.mqtt_mock()
        sched = NonCallableMock(spec_set=[])
        topic = "a/b/c"
        struct_fmt = "!ff"
        value = (3.0, 3.0)
        handle = Handle(mqtt=mqtt, sched=sched, topic=topic, qos=0, retain=True,
                        ser=Struct(struct_fmt, "SomeDesc"))

        cb = Mock(spec_set=[])
        _token = handle.sub(cb, wants_handle=True)

        test_topic = "a/+/c"
        handle.on_publish(topic=test_topic,
                          payload=struct.pack(struct_fmt, *value),
                          retained=False, duplicate=False)
        mqtt.assert_called_once_with(topic=test_topic, ser=handle.ser,
                                     qos=handle.qos, retain=handle.retain)
        sub_handle = mqtt()
        cb.assert_called_once_with(value, handle=sub_handle)
        mqtt.reset_mock(return_value=True)
        cb.reset_mock()

        test_topic = "a/#"
        handle.on_publish(topic=test_topic,
                          payload=struct.pack(struct_fmt, *value),
                          retained=False, duplicate=False)
        mqtt.assert_called_once_with(topic=test_topic, ser=handle.ser,
                                     qos=handle.qos, retain=handle.retain)
        sub_handle = mqtt()
        cb.assert_called_once_with(value, handle=sub_handle)
        cb.reset_mock()

        handle.on_publish(topic=test_topic,
                          payload=bytes([1]),
                          retained=False, duplicate=False)
        cb.assert_not_called()

    def test_aux(self):
        """ Test __eq__, __hash__ and __contains__ and change_ser. """

        mqtt = self.mqtt_mock()
        sched = NonCallableMock(spec_set=[])
        other_ser = Struct("!HH", "SomeDesc")
        ser = Struct("!ff", "SomeDesc")
        handle1 = Handle(mqtt=mqtt, sched=sched, topic="a/b/2",
                         ser=ser, qos=0, retain=True)
        handle2 = Handle(mqtt=mqtt, sched=sched, topic="a/b/3", ser=handle1.ser,
                         qos=handle1.qos, retain=handle1.retain)

        self.assertEqual(hash(handle1.topic), hash(handle1))
        self.assertNotEqual(handle1, handle2)
        self.assertEqual(handle1, handle1)

        self.assertIn(("a", "b", "2"), handle1)
        self.assertNotIn(("a", "b", "2"), handle2)

        self.assertNotIn(("a", "c", "2"), handle1)
        self.assertNotIn(("a", "c", "2"), handle2)

        self.assertIn(("a", "+", "2"), handle1)
        self.assertNotIn(("a", "+", "2"), handle2)

        self.assertIn(("a", "+", "+"), handle1)
        self.assertIn(("a", "+", "+"), handle2)

        self.assertIn(("a", "b", "+"), handle1)
        self.assertIn(("a", "b", "+"), handle2)

        self.assertIn(("a", "+", "2"), handle1)
        self.assertNotIn(("a", "+", "2"), handle2)

        self.assertNotIn(("a", "b", "2", "7"), handle1)
        self.assertIn(("a", "#"), handle1)

        self.assertIs(ser, handle1.ser)
        handle1.change_ser(other_ser)
        self.assertIs(other_ser, handle1.ser)

    def test_publish_meta(self):
        """ Test publishing meta data. """

        mqtt = self.mqtt_mock()
        sched = NonCallableMock(spec_set=["after"])
        topic = "a/+/b"
        meta_topic = topic.replace("+", "*")
        fmt_topic = "fmt/" + meta_topic
        desc_topic = "desc/" + meta_topic
        struct_fmt = "!HH"
        desc = "SomeDesc"
        ser = Struct(struct_fmt, desc)
        fmt = "struct/" + struct_fmt
        handle = Handle(mqtt=mqtt, sched=sched, topic=topic, ser=ser,
                        qos=1, retain=True)
        handle.publish_meta()
        mqtt.publish.assert_has_calls((call(topic=desc_topic, qos=1,
                                            payload=desc.encode(), retain=True),
                                       call(topic=fmt_topic, qos=1,
                                            payload=fmt.encode(), retain=True)),
                                      any_order=True)
        mqtt.publish.reset_mock()

        handle.topic = "a/#"
        handle.chunks = handle.topic.split("/")
        self.assertRaises(RuntimeError, handle.publish_meta)
        self.assertRaises(RuntimeError, handle.publish_meta)
        mqtt.publish.assert_not_called()

    def test_sub(self):
        """ Test subbing and and unsubbing. """

        mqtt = self.mqtt_mock()
        sched = NonCallableMock(spec_set=["after"])
        topic = "SomeTopic"
        ser = Struct("!HH", "SomeDesc")
        handle = Handle(mqtt=mqtt, sched=sched, topic=topic, ser=ser,
                        qos=1, retain=True)

        cb1 = Mock(spec_set=[])
        _token1 = handle.sub(cb1, wants_delivery=True)
        handle.on_publish(topic, struct.pack("!HH", 1, 2), True, False)
        cb1.assert_called_once_with((1, 2), duplicate=False, retained=True)
        cb1.reset_mock()
        handle.on_publish(topic, struct.pack("!HH", 3, 4), False, False)
        cb1.assert_called_once_with((3, 4), duplicate=False, retained=False)
        cb1.reset_mock()
        cb2 = Mock(spec_set=[])
        _token2 = handle.sub(cb2, wants_handle=True, wants_delivery=True)
        cb1.assert_not_called()
        cb2.assert_called_once_with((1, 2), handle=handle,
                                    duplicate=True, retained=True)
