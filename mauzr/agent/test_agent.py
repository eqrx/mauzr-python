""" Agent module test. """

import logging
import sys
from contextlib import contextmanager
import unittest
from unittest.mock import Mock, NonCallableMock, call
from mauzr.agent import AgentEvent as AE
import mauzr.agent
from mauzr.serializer import Serializer

class AgentTest(unittest.TestCase):
    """ Test Agent class. """

    AgentClass = mauzr.agent.Agent

    def shell_mock(self, agent_name):
        """ Create a shell mock. """

        handles = {}
        def _mqtt_side(topic, ser, qos, retain):
            self.assertTrue(ser is None or isinstance(ser, Serializer))
            self.assertEqual(1, qos)
            self.assertTrue(retain)
            tl_topic = topic
            if topic == f"cfg/testshell/{agent_name}":
                def _child(topic, ser, qos, retain):
                    self.assertTrue(ser is None or isinstance(ser, Serializer))
                    self.assertEqual(1, qos)
                    self.assertTrue(retain)
                    new_topic = f"{tl_topic}/{topic}"
                    mock = Mock(spec=["sub", "ser"])
                    return handles.setdefault(new_topic, mock)
                mock = Mock(spec=["child"],
                            child=Mock(spec_set=[], side_effect=_child))
                return handles.setdefault(topic, mock)
            return handles.setdefault(topic, Mock(spec=["sub", "ser",
                                                        "change_ser"]))

        tasks = {}
        def _sched_side(interval, cb, *_args, **_kwargs):
            self.assertTrue(interval is None or
                            isinstance(interval, (float, int)))
            self.assertTrue(callable(cb))
            return tasks.setdefault(cb, Mock(spec_set=["set", "enable",
                                                       "disable"]))

        sched = NonCallableMock(spec_set=["every", "after", "tasks"],
                                tasks=tasks,
                                after=Mock(spec_set=[],
                                           side_effect=_sched_side),
                                every=Mock(spec_set=[],
                                           side_effect=_sched_side))
        shell_log = logging.getLogger()
        s = NonCallableMock(spec_set=["name", "sched", "mqtt", "handles",
                                      "log", "agent_changed", "every",
                                      "after"],
                            handles=handles, log=shell_log, sched=sched,
                            agent_changed=Mock(spec_set=[]),
                            mqtt=Mock(side_effect=_mqtt_side,
                                      log=shell_log.getChild("mqtt")))
        s.name = "testshell"
        return s

    def ready_agent(self, agent):
        """ Ready the given agent. """

        agent_changed = agent.shell.agent_changed

        self.assertEqual(2, agent_changed.call_count)

        agent_changed.assert_has_calls([call(agent, AE.WANTS_CREATION),
                                        call(agent, AE.WANTS_DEACTIVATION)])
        agent.shell.agent_changed.reset_mock()
        topic = f"cfg/{agent.shell.name}/{agent.name}/log_level"
        agent.shell.handles[topic].sub.call_args[0][0]("info")
        agent_changed.assert_called_once_with(agent, AE.WANTS_ACTIVATION)
        agent_changed.reset_mock()

    def test_output_topic(self):
        """Test dynamic output operations. """

        agent_name = "testagent"
        shell = self.shell_mock(agent_name)
        agent = self.AgentClass(shell, agent_name)
        name = "SomeName"
        cfg_topic = "cfg/testshell/testagent"
        prefix = cfg_topic + "/"
        #value = "Somevalue"
        handle_valid = shell.mqtt("data/a", ser=None, qos=1, retain=True)
        handle_valid.ser.fmt = "struct/!ff"
        ser = handle_valid.ser
        handle_invalid = shell.mqtt("data/b", ser=None, qos=1, retain=True)
        handle_invalid.ser.fmt = "str"

        self.ready_agent(agent)
        self.assertTrue(agent.ready)
        agent.output_topic(name=name, regex=r"struct\/!ff", desc="SomeDesc")
        self.assertFalse(agent.ready)

        cfg_cb = shell.handles[prefix+name].sub.call_args[0][0]
        cfg_cb(handle_invalid)
        self.assertFalse(agent.ready)
        self.assertEqual("str", handle_invalid.ser.fmt)
        self.assertEqual("struct/!ff", handle_valid.ser.fmt)
        cfg_cb(handle_valid)
        self.assertIs(ser, handle_valid.ser)
        handle_valid.change_ser.assert_not_called()
        self.assertEqual("str", handle_invalid.ser.fmt)
        self.assertEqual("struct/!ff", handle_valid.ser.fmt)
        self.assertTrue(agent.ready)
        handle_valid.assert_not_called()
        value = object()
        getattr(agent, name)(value)
        handle_valid.assert_called_once_with(value)

        ser = object
        name = "data/othername"
        agent.output_topic(name=name, regex=r"struct\/!ff", desc="SomeDesc",
                           ser=ser)
        cfg_cb = shell.handles[prefix+name].sub.call_args[0][0]
        cfg_cb(handle_valid)
        handle_valid.change_ser.assert_called_once_with(ser)

    def test_input_topic(self):
        """ Test dynamic input operations. """

        # pylint: disable=too-many-locals

        agent_name = "testagent"
        shell = self.shell_mock(agent_name)
        agent = self.AgentClass(shell, agent_name)
        agent.on_input = Mock()
        name = "SomeName"
        cfg_topic = f"cfg/{shell.name}/{agent_name}"
        value = "Somevalue"
        fmt_valid = "struct/!ff"
        fmt_invalid = "supsup"
        handle_valid = shell.mqtt("data/a", ser=None, qos=1, retain=True)
        handle_valid.ser.fmt = fmt_valid
        ser = handle_valid.ser
        handle_invalid = shell.mqtt("data/b", ser=None, qos=1, retain=True)
        handle_invalid.ser.fmt = fmt_invalid

        self.assertFalse(agent.ready)
        self.ready_agent(agent)
        self.assertTrue(agent.ready)

        sub = {"wants_delivery": True}
        agent.input_topic(name=name, regex=r"struct\/!ff",
                          desc="SomeDesc", sub=sub)
        self.assertFalse(agent.ready)
        cfg_cb = shell.handles[cfg_topic+"/"+name].sub.call_args[0][0]
        cfg_cb(handle_invalid)
        self.assertFalse(agent.ready)
        cfg_cb(handle_valid)
        self.assertEqual(fmt_invalid, handle_invalid.ser.fmt)
        self.assertEqual(fmt_valid, handle_valid.ser.fmt)
        self.assertTrue(agent.ready)
        handle_valid.sub.assert_not_called()
        handle_invalid.sub.assert_not_called()

        with agent:
            handle_valid.sub.assert_called_once()
            handle_invalid.sub.assert_not_called()
            data_cb = handle_valid.sub.call_args[0][0]
            self.assertEqual(1, len(handle_valid.sub.call_args[0]))
            self.assertEqual(sub, handle_valid.sub.call_args[1])
            self.assertEqual(3, sys.getrefcount(handle_valid.sub()))
            agent.on_input.assert_not_called()
            self.assertIs(ser, handle_valid.ser)
            handle_valid.change_ser.assert_not_called()
            data_cb(value)
            agent.on_input.assert_called_once_with(value)
        self.assertEqual(2, sys.getrefcount(handle_valid.sub()))

        ser = object
        name = "data/othername"
        agent.input_topic(name=name, regex=r"struct\/!ff",
                          desc="SomeDesc", ser=ser)
        cfg_cb = shell.handles[cfg_topic+"/"+name].sub.call_args[0][0]
        cfg_cb(handle_valid)
        handle_valid.change_ser.assert_called_once_with(ser)

    def test_static_input(self):
        """ Test static input operations. """

        agent_name = "testagent"
        name1 = "SomeName"
        name2 = "SomeOtherName"
        shell = self.shell_mock(agent_name)
        agent = self.AgentClass(shell, agent_name)
        cfg_topic = "cfg/testshell/testagent"
        self.ready_agent(agent)
        cb1 = Mock()
        cb2 = Mock()
        handle1 = shell.handles[cfg_topic].child(topic=name1, ser=None,
                                                 qos=1, retain=True)
        handle2 = shell.handles[cfg_topic].child(topic=name2, ser=None,
                                                 qos=1, retain=True)

        self.assertEqual(2, sys.getrefcount(handle1.sub()))
        self.assertEqual(2, sys.getrefcount(handle2.sub()))
        sub = {"wants_delivery": True}
        agent.static_input(handle1, cb1, sub=sub)
        self.assertEqual(2, sys.getrefcount(handle1.sub()))
        self.assertEqual(2, sys.getrefcount(handle2.sub()))
        with agent:
            self.assertEqual(1, len(handle1.sub.call_args[0]))
            self.assertEqual(sub, handle1.sub.call_args[1])
            self.assertEqual(3, sys.getrefcount(handle1.sub()))
            self.assertEqual(2, sys.getrefcount(handle2.sub()))
            agent.static_input(handle2, cb2)
            self.assertEqual(3, sys.getrefcount(handle1.sub()))
            self.assertEqual(3, sys.getrefcount(handle2.sub()))
        self.assertEqual(2, sys.getrefcount(handle1.sub()))
        self.assertEqual(2, sys.getrefcount(handle2.sub()))
        with agent:
            self.assertEqual(3, sys.getrefcount(handle1.sub()))
            self.assertEqual(3, sys.getrefcount(handle2.sub()))
            agent.rm_static_input(handle1)
            self.assertEqual(2, sys.getrefcount(handle1.sub()))
            self.assertEqual(3, sys.getrefcount(handle2.sub()))
        self.assertEqual(2, sys.getrefcount(handle1.sub()))
        self.assertEqual(2, sys.getrefcount(handle2.sub()))

    def test_activation(self):
        """ Test activation handling. """

        cm1_on = False
        @contextmanager
        def _cm1():
            nonlocal cm1_on
            cm1_on = True
            yield
            cm1_on = False

        cm2_on = False
        @contextmanager
        def _cm2():
            nonlocal cm2_on
            cm2_on = True
            yield
            cm2_on = False

        agent_name = "testagent"
        shell = self.shell_mock(agent_name)
        agent_changed = shell.agent_changed
        agent = self.AgentClass(shell, agent_name)
        self.assertRaises(RuntimeError, agent.__enter__)
        self.assertFalse(agent.ready)
        self.assertFalse(agent.active)
        self.ready_agent(agent)
        self.assertTrue(agent.ready)
        self.assertFalse(agent.active)
        agent.add_context(_cm1)
        self.assertFalse(cm1_on)
        with agent:
            self.assertTrue(cm1_on)
            self.assertFalse(cm2_on)
            agent.add_context(_cm2)
            self.assertTrue(cm2_on)
            self.assertTrue(agent.ready)
            self.assertTrue(agent.active)
        self.assertTrue(agent.ready)
        self.assertFalse(agent.active)
        self.assertFalse(cm1_on)
        self.assertFalse(cm2_on)

        with agent:
            shell.agent_changed.assert_not_called()
            agent.discard()
            agent_changed.assert_called_once_with(agent, AE.WANTS_DESTRUCTION)
            agent_changed.assert_called_once_with(agent, AE.WANTS_DESTRUCTION)
            self.assertFalse(agent.active)

    def test_option(self):
        """ Test option handling. """

        name = "SomeName"
        fmt = "struct/!ff"
        desc = "SomeDescription"
        value = "SomeValue"
        #ser = None
        #cb = None
        #attr = None
        #restart = True

        agent_name = "testagent"
        shell = self.shell_mock(agent_name)
        agent = self.AgentClass(shell, agent_name)
        agent_changed = shell.agent_changed
        prefix = "cfg/testshell/testagent/"

        self.ready_agent(agent)
        agent_changed.assert_not_called()
        self.assertTrue(agent.ready)
        self.assertFalse(agent.active)

        agent.option(name, fmt, desc)
        agent_changed.assert_called_once_with(agent, AE.WANTS_DEACTIVATION)
        self.assertFalse(agent.ready)
        self.assertFalse(agent.active)
        shell.handles[prefix+name].sub.assert_called_once()
        agent_changed.reset_mock()

        self.assertRaises(AttributeError, getattr, agent, name)
        shell.handles[prefix+name].sub.call_args[0][0](value)
        self.assertEqual(value, getattr(agent, name))
        self.assertTrue(agent.ready)
        self.assertFalse(agent.active)
        agent_changed.assert_has_calls([call(agent, AE.WANTS_DEACTIVATION),
                                        call(agent, AE.WANTS_ACTIVATION)])

    def test_start(self):
        """ Test instantiation. """

        agent_name = "testagent"
        shell = self.shell_mock(agent_name)
        agent = self.AgentClass(shell, agent_name)
        self.assertFalse(agent.active)
        self.assertFalse(agent.ready)

        cfg_topic = f"cfg/{shell.name}/{agent.name}"
        cfg_child = shell.handles[cfg_topic].child
        self.assertTrue(cfg_child.call_count > 0)
        self.assertIn(cfg_topic+"/log_level", shell.handles)

        status_topic = f"status/{shell.name}/{agent.name}"
        shell.handles[status_topic].assert_called_once_with(False)
        self.assertEqual(2, shell.mqtt.call_count)

        self.ready_agent(agent)

    def test_on_input_unimplemented(self):
        """ Test calling of the unimplemented input method. """

        agent_name = "testagent"
        shell = self.shell_mock(agent_name)
        agent = self.AgentClass(shell, agent_name)
        agent.on_input(None)

    def test_scheduler(self):
        """ Test scheduler wrapping. """

        agent_name = "testagent"
        shell = self.shell_mock(agent_name)
        sched = shell.sched
        after = sched.after
        every = sched.every
        agent = self.AgentClass(shell, agent_name)
        delay = 6

        args = ("x", 2)
        kwargs = {"a": 4}

        cb1 = Mock(spec_set=[])
        after.reset_mock()
        agent.after(delay, cb1, *args, **kwargs)
        after.assert_called_once()
        self.assertEqual(4, len(after.call_args[0]))
        self.assertEqual(delay, after.call_args[0][0])
        self.assertEqual(args, after.call_args[0][2:])
        self.assertEqual(kwargs, after.call_args[1])
        cb1.assert_not_called()
        after.call_args[0][1](*args, **kwargs)
        after.assert_called_once()
        cb1.assert_called_once_with(*args, **kwargs)


        cb2 = Mock(spec_set=[])
        every.reset_mock()
        agent.every(delay, cb2, *args, **kwargs)
        every.assert_called_once()
        self.assertEqual(4, len(every.call_args[0]))
        self.assertEqual(delay, every.call_args[0][0])
        self.assertEqual(args, every.call_args[0][2:])
        self.assertEqual(kwargs, every.call_args[1])
        cb2.assert_not_called()
        every.call_args[0][1](*args, **kwargs)
        every.assert_called_once()
        cb2.assert_called_once_with(*args, **kwargs)
