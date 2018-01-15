""" Data conversion helpers. """

import enum
import mauzr.serializer
from mauzr.serializer import Bool as BS
from mauzr.serializer import String as SS

__author__ = "Alexander Sowitzki"


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


def aggregate(core, handler, default, inputs, output):
    """ Aggregates multiple topics to a single one.

    :param core: Core instance.
    :type core: object
    :param handler: Callable used for aggregation. Receives a dict of topic
                    states, the current topic and the current value as
                    arguments and is expected to return the new output
                    value or None.
    :type handler: callable
    :param default: Initial values to publish. May be None.
    :type default: object
    :param inputs: A list of tuples describing each input by listing topic and
                   serializer. When a message arrives for these topics,
                   it is added to the value list and passed to the
                   hander callable.
    :type inputs: tuple
    :param output: Topic, serializer and QoS of input.
    :type output: tuple

    **Required core units**:

        - mqtt
    """

    values = {}
    last = None
    log = core.logger(f"<aggregate@{output[0]}>")
    core.mqtt.setup_publish(*output, default)

    def _on_message(in_topic, value):
        nonlocal last
        values[in_topic] = value
        ret = handler(values, in_topic, value)
        if ret is not None and (last is None or last != ret):
            last = ret
            core.mqtt.publish(output[0], ret, True)
            log.debug("Received for %s: %s - Publishing: %s",
                      in_topic, value, ret)

    for in_topic, deserializer, qos in inputs:
        values[in_topic] = None
        core.mqtt.subscribe(in_topic, _on_message, deserializer, qos)


# pylint: disable = redefined-builtin
def delay(core, condition, amount, payload, retain, input, output):
    """ Allows to send payload when a condition is met after a defined delay.

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
    :param input: Topic, deserializer and QoS of input.
    :type input: tuple
    :param output: Topic, serializer and QoS of input.
    :type output: tuple

    **Required core units**:

        - mqtt
    """

    log = core.logger(f"<delay@{input[0]}-{output[0]}>")
    core.mqtt.setup_publish(*output)

    def _after_delay():
        core.mqtt.publish(output[0], payload, retain)
        log.debug("Publishing: %s", payload)

    def _on_message(topic, message):
        if condition(message):
            task.enable()
        log.debug("Received: %s - delaying", message)

    core.mqtt.subscribe(input[0], _on_message, input[1], input[2])
    task = core.scheduler(_after_delay, amount, single=True)


# pylint: disable = redefined-builtin
def convert(core, mapper, retain, default, input, output):
    """ Convert the messages of one topic into messages in some other.

    :param core: Core instance.
    :type core: object
    :param mapper: If input has this value, the payload will be published.
    :type mapper: object
    :param retain: If True the retain flag is set.
    :type retain: bool
    :param default: Initial values to publish. May be None.
    :type default: object
    :param input: Topic, deserializer and QoS of input.
    :type input: tuple
    :param output: Topic, serializer and QoS of input.
    :type output: tuple

    **Required core units**:

        - mqtt
    """

    log = core.logger(f"<convert@{input[0]}→{output[0]}>")
    core.mqtt.setup_publish(*output, default)
    last = None

    def _on_message(topic, value):
        nonlocal last
        ret = mapper(value)
        if ret is not None and (not retain or last != ret or last is None):
            last = ret
            core.mqtt.publish(output[0], ret, retain)
            log.debug("Received %s - Published: %s", value, ret)
        else:
            log.debug("Received %s - Converted to: %s (Not published)",
                      value, ret)

    core.mqtt.subscribe(input[0], _on_message, input[1], input[2])


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
        - ``topic``/*request* (``?``) - Bool requesting the output to be \
                                        enabled or disabled.
        - ``topic``/*request/toggle* (``?``) - Request the output to \
                                               be toggled.

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

    aggregate(core,
              lambda st, tpc, val: st[con_tpc] == BC.FREE and not st[topic],
              True,
              ((con_tpc, BCS, 0), (topic, BS, 0)), (on_allowed, BS, 0))

    aggregate(core,
              lambda st, tpc, val: st[con_tpc] == BC.FREE and st[topic],
              False,
              ((con_tpc, BCS, 0), (topic, BS, 0)),
              (off_allowed, BS, 0))

    aggregate(core, _handler, False,
              ((topic, BS, 0), (con_tpc, BCS, 0),
               (req_tpc, BS, 0), (tgl_tpc, BS, 0)),
              (topic, BS, 0))


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

    convert(core, converter, True, None,
            (topic, ser, 0), (topic + "/str", SS, 0))


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

    convert(core, converter, retain, None,
            (topic + "/str", SS, 0), (topic, ser, 0))
