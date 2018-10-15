""" Generic elements. """

from contextlib import contextmanager
from mauzr.agents.gui import ConfirmationMixin, Element
from mauzr.agents.gui import OutputMixin, TextInputMixin, ColorInputMixin

__author__ = "Alexander Sowitzki"

class Controller(OutputMixin, TextInputMixin, ColorInputMixin, Element):
    """ Element for data toggler. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_agent(arm=True)

class Indicator(ConfirmationMixin, TextInputMixin, ColorInputMixin, Element):
    """ An element on the GUI window. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout_task = None
        self.option("timeout", "struct/!I", "Timeout delay in seconds")
        self.input_topic("timeout_input", r".*", "Timeout input",
                         cb=self.reset_timeout)
        self.add_context(self.__indicator_context)

        self.update_agent(arm=True)

    @contextmanager
    def __indicator_context(self):
        """ Context for the indicator. """

        if self.timeout:
            self.timeout_task = self.after(self.timeout,
                                           self.on_new_state).enable()
        yield
        self.timeout_task = None

    def reset_timeout(self, _value):
        """ Apply value to element and reset the task. """

        if self.timeout_task:
            self.timeout_task.enable()
