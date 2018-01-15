""" Inficator elements. """

from mauzr.serializer import Bool as BS
from mauzr.gui import TextMixin, ColorStateMixin, RectBackgroundMixin
from mauzr.gui import BaseElement, ColorState

__author__ = "Alexander Sowitzki"


class AgentIndicator(ColorStateMixin, TextMixin, RectBackgroundMixin,
                     BaseElement):

    """ Indicate the presence of a mauzr agent.

    :param core: Core instance.
    :type core: object
    :param name: Agent name.
    :type name: str
    :param placement: Center and size of the element.
    :type placement: tuple
    """

    def __init__(self, core, name, placement):
        BaseElement.__init__(self, *placement)
        RectBackgroundMixin.__init__(self)
        TextMixin.__init__(self, name)
        conditions = {ColorState.UNKNOWN: lambda v: v is None,
                      ColorState.ERROR: lambda v: v is False,
                      ColorState.INFORMATION: lambda v: v is True}
        ColorStateMixin.__init__(self, conditions)
        topic = "{}/agents/{}".format(name.split("-")[0], name)
        core.mqtt.subscribe(topic, self._on_state_change, BS, 2)
        if topic.split("/")[-1] == core.config.id:
            core.mqtt.connection_listeners.append(self._on_connection_change)

    def _on_connection_change(self, status):
        # In any case, connection change means the value in invalid
        self._update_state(None)
        self.state_acknowledged = False

    def _on_state_change(self, _topic, value):
        # Update state
        self._update_state(value)
        self.state_acknowledged = False

    def _on_click(self):
        # Assume click means acknowledge
        self.state_acknowledged = True


class Indicator(ColorStateMixin, TextMixin, RectBackgroundMixin, BaseElement):
    """ Display for the value of a topic.

    :param core: Core instance.
    :type core: object
    :param fmt: Format to use for displaying the topic value. Is expected to \
                be in curly braces and with implicit position reference. \
                Will be concatenated to the internal format.
    :type fmt: str
    :param state_conditions: Dictionary mapping :class:`mauzr.gui.ColorState`\
                             to functions. The function receives one
                             parameter and should return True if the value \
                             indicates the mapped state.
    :type state_conditions: dict
    :param timeout: If not None, an update of the topic is expected each \
                    ``timeout`` milliseconds. If a timeout occurs, \
                    the indicator is going into \
                    :class:`mauzr.gui.ColorState.ERROR`.
    :type timeout: int
    :param input: Topic deserializer and QoS of input.
    :type input: tuple
    :param placement: Center and size of the element.
    :type placement: tuple
    """

    # pylint: disable = redefined-builtin
    def __init__(self, core, fmt, state_conditions, timeout,
                 input, placement):
        BaseElement.__init__(self, *placement)
        RectBackgroundMixin.__init__(self)
        TextMixin.__init__(self, fmt)
        state_conditions[ColorState.UNKNOWN] = lambda v: v is None
        ColorStateMixin.__init__(self, state_conditions)

        self.state_acknowledged = True
        self._fmt = fmt
        self._timer = None
        if timeout:
            self._timer = core.scheduler(self._on_timeout, timeout,
                                         single=True).enable()

        core.mqtt.subscribe(input[0], self._on_message, input[1], input[2])

    def _on_timeout(self):
        # No update, complain
        self._state = ColorState.ERROR
        self.state_acknowledged = False

    def _on_message(self, _topic, value):
        self._update_state(value)
        # Update text
        self._text = self._fmt.format(value)
        if self._timer is not None:
            # Delay timeout
            self._timer.enable()

    def _on_click(self):
        # Assume click means acknowledge
        self.state_acknowledged = True
