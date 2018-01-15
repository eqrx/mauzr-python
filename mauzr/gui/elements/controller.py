""" Controller elements. """

from mauzr.serializer import Bool as BS
from mauzr.gui import TextMixin, RectBackgroundMixin
from mauzr.gui import BaseElement

__author__ = "Alexander Sowitzki"


class SimpleController(TextMixin, RectBackgroundMixin, BaseElement):
    """ Controller for sending a value when clicked.

    :param core: Core instance.
    :type core: object
    :param cond_topic: Topic that has to be True to send.
    :type cond_topic: str
    :param label: Label to prepend the value with. Is separated from
                 it by ": ".
    :type label: str
    :param output: Topic, payload, QoS and retainment of the sender.
    :type output: str
    :param placement: Center and size of the element.
    :type placement: tuple
    """

    COLOR_READY = (0, 150, 0)
    """ Color that indicates a tap sends a value. """
    COLOR_NOT_READY = (100, 100, 100)
    """ Color that indicates the condition is not met. """

    def __init__(self, core, cond_topic, label, output, placement):
        BaseElement.__init__(self, *placement)
        RectBackgroundMixin.__init__(self)
        TextMixin.__init__(self, label)

        qos = output[2]
        self._send_topic = output[0]
        self._payload = output[1]
        self._retain = output[3]
        self._mqtt = core.mqtt
        self._ready = False

        core.mqtt.subscribe(cond_topic, self._on_change, BS, qos)
        core.mqtt.setup_publish(self._send_topic, BS, qos)

    def _on_change(self, _topic, value):
        self._ready = value

    def _on_click(self):
        if self._ready:
            self._mqtt.publish(self._send_topic, self._payload, self._retain)

    @property
    def _color(self):
        if self._ready:
            return self.COLOR_READY
        return self.COLOR_NOT_READY


class ToggleController(TextMixin, RectBackgroundMixin, BaseElement):
    """ Controller for toggling a values between two states.

    :param core: Core instance.
    :type core: object
    :param retain: True if publish shall be retained.
    :type retain: bool
    :param label: Label to prepend the value with. Is separated from
                 it by ": ".
    :type label: str
    :param output: Topic and QoS of output.
    :type output: tuple
    :param placement: Center and size of the element.
    :type placement: tuple
    """

    COLOR_ON = (150, 150, 0)
    """ Color for on state. """
    COLOR_OFF = (0, 100, 200)
    """ color for off state. """
    COLOR_UNKNOWN = (70, 70, 70)
    """ Color for unknown state. """

    def __init__(self, core, retain, label, output, placement):
        BaseElement.__init__(self, *placement)
        RectBackgroundMixin.__init__(self)
        TextMixin.__init__(self, label)

        core.mqtt.subscribe(output[0], self._on_change, BS, output[1])
        core.mqtt.setup_publish(output[0], BS, output[1])

        self._retain = retain
        self._topic = output[0]
        self._mqtt = core.mqtt
        self._current = None

    def _on_change(self, _topic, value):
        self._current = value

    def _on_click(self):
        self._mqtt.publish(self._topic, not self._current, self._retain)

    @property
    def _color(self):
        if self._current is None:
            return self.COLOR_UNKNOWN
        elif self._current:
            return self.COLOR_ON
        return self.COLOR_OFF
