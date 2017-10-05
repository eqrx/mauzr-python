"""
.. module:: tests.conftest
   :platform: cpython
   :synopsis: Fixtures for testing.

.. moduleauthor:: Alexander Sowitzki <dev@eqrx.net>
"""

import enum
import time
import pytest
import mauzr.platform.cpython

def interaction(func):
    """ Decorator for mockups.

    Decorate functions that are called by the unit under test. This
    decorator ensures the mockup is not already stopped and calls
    :func:`MQTTMockup._on_interaction`.
    """

    def _wrapper(*args):
        # pylint: disable=protected-access
        self = args[0]
        assert not self._finish_event.is_set()
        func(*args)
        self._on_interaction()
    return _wrapper

class MQTTMockup:
    """ a """

    class _Type(enum.Enum):
        SUB = enum.auto()
        SET = enum.auto()
        PUB = enum.auto()
        INJ = enum.auto()

    # pylint: disable=redefined-outer-name
    def __init__(self, core):
        import threading
        import collections

        self._expected = []
        self._actual = []
        self._publishes = []
        self._finish_event = threading.Event()
        self._subscriptions = collections.defaultdict(list)
        self._publish_task = core.scheduler(self._execute_publish, 0, False)

    def sub(self, topic, serializer, qos):
        """ Expect a :func:`mauzr.platform.mqtt.subscribe` call.

        :param topic: MQTT topic.
        :type topic: str
        :param serializer: Payload serializer.
        :type serializer: object
        :param qos: QoS level.
        :type qos: int
        """

        self._expected.append((self._Type.SUB,) + (topic, serializer, qos))

    def set(self, topic, serializer, qos):
        """ Expect a :func:`mauzr.platform.mqtt.setup_publish` call.

        :param topic: MQTT topic.
        :type topic: str
        :param serializer: Payload serializer.
        :type serializer: object
        :param qos: QoS level.
        :type qos: int
        """

        self._expected.append((self._Type.SET,) + (topic, serializer, qos))

    def exp(self, topic, payload, retain):
        """ Expect a :func:`mauzr.platform.mqtt.publish` call.

        :param topic: MQTT topic.
        :type topic: str
        :param payload: Message payload.
        :type payload: object
        :param retain: Retain value.
        :type retain: bool
        """

        self._expected.append((self._Type.PUB,) + (topic, payload, retain))

    def inj(self, topic, payload):
        """ Send a message to all listeners.

        :param topic: MQTT topic.
        :type topic: str
        :param payload: Message payload.
        :type payload: object
        """

        self._expected.append((self._Type.INJ,) + (topic, payload))

    @interaction
    def setup_publish(self, *args):
        """ Mimic :func:`mauzr.platform.mqtt.setup_publish` and log event. """

        self._actual.append((self._Type.SET,) + tuple(args))

    @interaction
    def subscribe(self, *args):
        """ Mimic :func:`mauzr.platform.mqtt.subscribe`
        and log event & subscription. """

        args = list(args)
        topic = args[0]
        callback = args.pop(1)
        self._subscriptions[topic].append(callback)
        self._actual.append((self._Type.SUB,) + tuple(args))

    @interaction
    def publish(self, *args):
        """ Mimic :func:`mauzr.platform.mqtt.publish` and log event. """

        self._actual.append((self._Type.PUB,) + tuple(args))

    def _execute_publish(self):
        if self._publishes:
            topic, value = self._publishes.pop(0)
            callbacks = self._subscriptions[topic]
            assert callbacks

            [c(topic, value) for c in callbacks]
        else:
            self._publish_task.disable()

    def _on_interaction(self):
        while True:
            if not self._expected:
                self._finish_event.set()
                break
            elif self._expected[0][0] == self._Type.INJ:
                args = self._expected.pop(0)[1:]
                self._publishes.append(args)
                self._publish_task.enable()
            elif not self._actual:
                break
            else:
                expected = self._expected.pop(0)
                actual = self._actual.pop(0)
                assert expected == actual

    def __call__(self, delay, timeout):
        self._publish_task.enable()
        self._finish_event.wait(timeout)
        time.sleep(delay)
        assert not self._actual and not self._expected, \
                "Elements missing: {}".format(self._expected)

class CoreMockup(mauzr.platform.cpython.Core):
    """ CPython core with mockup elements. """

    def setup_mqtt(self):
        """ Use :class:`MQTTMockup`. """

        self.mqtt = MQTTMockup(self)


@pytest.fixture(scope="function")
def core():
    """ Create a mauzr core fixture with a an MQTT mockup. """

    c = CoreMockup("mauzr", "tester")
    c.setup_mqtt()
    yield c

@pytest.fixture(scope="session")
def merge():
    """ Create a configuration fixture for data merging. """

    class _MergeConfig:
        in_tpcs = ["abc/a0", "abc/a1", "abc/a2"]
        out_tpc = "abc"
        deser = object()
        ser = object()
        qos = 1
        dflt = 8

    yield _MergeConfig

@pytest.fixture(scope="session")
def split():
    """ Create a configuration fixture for data splitting. """

    class _SplitConfig:
        in_tpc = "abc"
        out_tpcs = ["abc/a0", "abc/a1", "abc/a2"]
        deser = object()
        ser = object()
        qos = 1
        dflt = 8

    yield _SplitConfig

@pytest.fixture(scope="session")
def conversion():
    """ Create a configuration fixture for data conversion. """

    class _ConversionConfig:
        in_tpc = "a"
        out_tpc = "b"
        deser = object()
        ser = object()
        qos = 1
        dflt = 1
        ret = True

    yield _ConversionConfig

@pytest.fixture(scope="session")
def delay():
    """ Create a configuration fixture for data delaying. """

    class _DelayConfig:
        in_tpc = "a"
        out_tpc = "b"
        deser = object()
        ser = object()
        qos = 1
        pay = None
        ret = True

    yield _DelayConfig
