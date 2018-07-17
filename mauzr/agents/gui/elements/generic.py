""" Generic elements. """

from contextlib import contextmanager
from mauzr.agents.gui import ConfirmationMixin, Element
from mauzr.agents.gui import OutputMixin, TextInputMixin, ColorInputMixin

__author__ = "Alexander Sowitzki"

class Controller(OutputMixin, TextInputMixin, ColorInputMixin, Element):
    """ Element for data toggler. """

class Indicator(ConfirmationMixin, TextInputMixin, ColorInputMixin, Element):
    """ An element on the GUI window. """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.timeout_task = self.after(None, self.on_timeout)
        self.option("timeout", "struct/f", "Timeout delay in seconds")
        self.input_topic("timeout_input", r".*", "Timeout input",
                         cb=self.reset_timeout)
        self.add_context(self.indicator_context)

    @contextmanager
    def indicator_context(self):
        """ Context for the indicator. """

        self.timeout_task.interval = self.timeout
        self.timeout_task.enable()
        yield
        self.timeout_task.disable()

    def on_timeout(self):
        """ Call when the value timed out. """

        self.state_acknowledged = False

    def reset_timeout(self, _value):
        """ Apply value to element and reset the task. """

        self.timeout_task.enable()
