""" Data conversion helpers. """
__author__ = "Alexander Sowitzki"

import enum
import mauzr.serializer
from mauzr.serializer import Bool as BS
from mauzr.serializer import String as SS

class BoolCondition(enum.Enum):
    """ Condition for boolean channels. """

    FORCE_OFF = 0
    """ Channel is forced to off. """
    FORCE_ON = 1
    """ Channel is forced to on. """
    FREE = 2
    """ Channel is free to change. """

BC = BoolCondition
BCS = mauzr.serializer.Enum(BC, "!H")

def aggregate(core, inputs, handler, default, out_topic, serializer, qos):
    """ Aggregates multiple topics to a single one.

    :param core: Core instance.
    :type core: object
    :param inputs: A list of tuples describing each input by listing topic and
                   serializer. When a message arrives for these topics,
                   it is added to the value list and passed to the
                   hander callable.
    :type inputs: tuple
    :param handler: Callable used for aggregation. Receives a dict of topic
                    states, the current topic and the current value as
                    arguments and is expected to return the new output
                    value or None.
    :type handler: callable
    :param default: Initial values to publish. May be None.
    :type default: object
    :param out_topic: Output topic.
    :type out_topic: str
    :param serializer: Output serializer.
    :type serializer: object
    :param qos: QoS for input and output.
    :type qos: int

    **Required core units**:

        - mqtt
    """

    values = {}
    last = None
    log = core.logger(f"<aggregate@{out_topic}>")
    core.mqtt.setup_publish(out_topic, serializer, qos, default)

    def _on_message(in_topic, value):
        nonlocal last
        values[in_topic] = value
        ret = handler(values, in_topic, value)
        if ret is not None and (last is None or last != ret):
            last = ret
            core.mqtt.publish(out_topic, ret, True)
            log.debug("Received for %s: %s - Publishing: %s",
                      in_topic, value, ret)

    for in_topic, deserializer in inputs:
        values[in_topic] = None
        core.mqtt.subscribe(in_topic, _on_message, deserializer, qos)

def delay(core, condition, amount, payload, retain,
          in_topic, out_topic, deserializer, serializer, qos):
    """ Allows to send a payload when a condition is met after a defined delay.

    :param core: Core instance.
    :type core: object
    :param condition: If this callable returns True when called with an
                      incoming message as argument, the timer ist started.
    :type condition: callable
    :param amount: Delay after which to trigger the message sending.
    :type amount: int
    :param payload: Message to send when timer expires.
    :type payload: object
    :param retain: If True the retain flag is set.
    :type retain: bool
    :param in_topic: Input topic.
    :type in_topic: str
    :param out_topic: Output topic.
    :type out_topic: str
    :param deserializer: Deserializer for the input.
    :type deserializer: object
    :param serializer: Output serializer.
    :type serializer: object
    :param qos: QoS for input and output.
    :type qos: int

    **Required core units**:

        - mqtt
    """

    log = core.logger(f"<delay@{in_topic}-{out_topic}>")
    core.mqtt.setup_publish(out_topic, serializer, qos)

    def _after_delay():
        core.mqtt.publish(out_topic, payload, retain)
        log.debug("Publishing: %s", payload)

    def _on_message(topic, message):
        if condition(message):
            task.enable()
        log.debug("Received: %s - delaying", message)

    core.mqtt.subscribe(in_topic, _on_message, deserializer, qos)
    task = core.scheduler(_after_delay, amount, single=True)

def split(core, in_topic, out_topics, deserializer, serializer, default, qos):
    """ Split a single topic into multiple.

    :param core: Core instance.
    :type core: object
    :param in_topic: Input topic.
    :type in_topic: str
    :param out_topics: List of output topics.
    :type out_topics: tuple
    :param deserializer: Deserializer for the input.
    :type deserializer: object
    :param serializer: Serializer for the outputs.
    :type serializer: object
    :param default: Default output value.
    :type default: object
    :param qos: QoS for input and output.
    :type qos: int

    **Required core units**:

        - mqtt
    """

    log = core.logger(f"<split@{in_topic}>")
    [core.mqtt.setup_publish(topic, serializer, qos, default)
     for topic, dflt in zip(out_topics, default)]

    def _on_message(_topic, values):
        log.debug("Received: %s", values)
        [core.mqtt.publish(topic, value, True)
         for topic, value in zip(out_topics, values)]

    core.mqtt.subscribe(in_topic, _on_message, deserializer, qos)

def merge(core, in_topics, out_topic, deserializer, serializer, default, qos):
    """ Merge multiple topics into one.

    :param core: Core instance.
    :type core: object
    :param in_topics: List of input topics.
    :type in_topics: tuple
    :param out_topic: Output topic
    :type out_topic: str
    :param deserializer: Deserializer for the inputs.
    :type deserializer: object
    :param serializer: Serializer for the output.
    :type serializer: object
    :param qos: QoS for input and output.
    :type qos: int
    :param default: Default input value.
    :type default: object
    :raise ValueError: If length if in_topics does not match default.

    **Required core units**:

        - mqtt
    """

    log = core.logger(f"<merge@{out_topic}>")
    values = list(default)
    if len(values) != len(in_topics):
        raise ValueError("Need as many default values as input topics")
    core.mqtt.setup_publish(out_topic, serializer, qos, values)
    core.mqtt.publish(out_topic, values, True)

    def _on_message(topic, value):
        i = in_topics.index(topic)
        values[i] = value
        core.mqtt.publish(out_topic, values, True)
        log.debug("Published: %s", values)

    [core.mqtt.subscribe(topic, _on_message, deserializer, qos)
     for topic in in_topics]

# pylint: disable=redefined-builtin
def convert(core, mapper, retain, default,
            in_topic, out_topic, deserializer, serializer, qos):
    """ Convert the messages of one topic into messages in some other.

    :param core: Core instance.
    :type core: object
    :param mapper: If input has this value, the payload will be published.
    :type mapper: object
    :param retain: If True the retain flag is set.
    :type retain: bool
    :param default: Initial values to publish. May be None.
    :type default: object
    :param in_topic: Topic of the input.
    :type in_topic: str
    :param out_topic: Topic of the output.
    :type out_topic: str
    :param deserializer: Deserializer for the input.
    :type deserializer: object
    :param serializer: Serializer for the output.
    :type serializer: object
    :param qos: QoS for input and output.
    :type qos: int

    **Required core units**:

        - mqtt
    """

    log = core.logger(f"<convert@{in_topic}→{out_topic}>")
    core.mqtt.setup_publish(out_topic, serializer, qos, default)
    last = None

    def _on_message(topic, value):
        nonlocal last
        ret = mapper(value)
        if ret is not None and (not retain or last != ret or last is None):
            last = ret
            core.mqtt.publish(out_topic, ret, retain)
            log.debug("Received %s - Published: %s", value, ret)
        else:
            log.debug("Received %s - Converted to: %s (Not published)",
                      value, ret)

    core.mqtt.subscribe(in_topic, _on_message, deserializer, qos)

def gate_bool(core, topic):
    """ Control a bool topic by applying a condition for it

    :param core: Core instance.
    :type core: object
    :param topic: Output topic to manage.
    :type topic: str

    **Required core units**:

        - mqtt

    **Input Topics:**

        - ``topic``/*condition* (``!H``) - :class:`BoolCondition` describing \
                                         what the output may do.
        - ``topic``/*request* (``?``) - Bool requesting the output to be enabled
                                      or disabled.
        - ``topic``/*request/toggle* (``?``) - Request the output to be toggled.

    **Output Topics:**

        - ``topic`` (`?`) - Bool describing if the output in enabled.
        - ``topic``/*on_allowed* (```?``) - Bool describing if output may be
                                         requested to be enabled.
        - ``topic``/*off_allowed* (``?``) - Bool describing if output may be
                                          requested to be disabled.
    """

    base = topic + "/"
    con_tpc = base + "condition"
    req_tpc = base + "request"
    tgl_tpc = req_tpc + "/toggle"
    on_allowed = base + "on_allowed"
    off_allowed = base + "off_allowed"

    def _handler(st, tpc, val):
        if st[con_tpc] == BC.FORCE_ON:
            return True
        elif st[con_tpc] == BC.FORCE_OFF:
            return False
        else:
            if tpc == req_tpc:
                return val
            elif tpc == tgl_tpc:
                return not st[topic]

    aggregate(core, ((con_tpc, BCS), (topic, BS)),
              lambda st, tpc, val: st[con_tpc] == BC.FREE and not st[topic],
              True, on_allowed, BS, 0)


    aggregate(core, ((con_tpc, BCS), (topic, BS)),
              lambda st, tpc, val: st[con_tpc] == BC.FREE and st[topic],
              False, off_allowed, BS, 0)

    aggregate(core, ((topic, BS), (con_tpc, BCS), (req_tpc, BS), (tgl_tpc, BS)),
              _handler, False, topic, BS, 0)

def to_string(core, topic, ser, converter=str):
    """ Convert messages from a topic into another topic as string.

    :param core: Core instance.
    :type core: object
    :param topic: Message will be read from topic and published to \
                  topic + "/str".
    :type topic: str
    :param ser: Serializer to use for deserialization
    :type ser: object
    :param converter: Callable to convert deserialized value to string.
    :type converter: callable
    """

    convert(core, converter, True, None, topic, topic + "/str", ser, SS, 0)

def from_string(core, topic, retain, ser, converter):
    """ Convert string messages from a topic into another topic and type.

    :param core: Core instance.
    :type core: object
    :param topic: Message will be read from topic + "/str" \
                  and published to topic.
    :type topic: str
    :param retain: If the published message shall be retained.
    :type retain: Bool
    :param ser: Serializer to use for serialization
    :type ser: object
    :param converter: Callable to convert deserialized string value to \
                      something interpretable by the serializer.
    :type converter: callable
    """

    convert(core, converter, retain, None, topic + "/str", topic, SS, ser, 0)
