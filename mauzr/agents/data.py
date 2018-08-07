""" Data conversion helpers. """

from contextlib import suppress, contextmanager
from mauzr.serializer import Eval
from mauzr import Agent

__author__ = "Alexander Sowitzki"


class Aggregator(Agent):
    """ Aggregates multiple inputs by using a converter function ."""

    def __init__(self, *args, **kwargs):
        self.values = {}
        self.output_value = None
        super().__init__(*args, **kwargs)

        self.option("inputs", "topics", "Input topics")
        self.option("converter", fmt=None, desc=None,
                    ser=Eval(shell=self.shell, desc="Aggregation method"))
        self.output_topic("output", r".*", "Output topic")

        self.update_agent(arm=True)

    @contextmanager
    def setup(self):
        if not callable(self.converter):
            raise ValueError("Converter is not callable")

        try:
            # Subscribe all inputs and yield.
            [self.static_input(h, self.on_input, sub={"wants_handle": True})
             for h in self.inputs]
            yield
        finally:
            # Unsubscribe all inputs.
            for h in self.inputs:
                with suppress(KeyError):
                    self.rm_static_input(h)

    def on_input(self, value, handle):
        topic, values = handle.topic, self.values

        values[topic] = value  # Save new value.
        try:
            # Put existing values and new value into converter.
            new_value = self.converter(values, topic, value)
        except KeyError:
            # Prevent race conditions.
            self.log.excption("Not all keys are present")
            return
        # Publish result.
        if not self.output.retain or new_value != self.output_value:
            self.output_value = new_value
            self.output(new_value)


class Converter(Agent):
    """ Convert an input via an converter function. """

    def __init__(self, *args, **kwargs):
        self.value = None
        super().__init__(*args, **kwargs)

        self.option("converter", fmt=None, desc=None,
                    ser=Eval(shell=self.shell, desc="Converter method"))
        self.output_topic("output", r".*", "Output topic")
        self.input_topic("input", r".*", "Input topic")
        self.update_agent(arm=True)

    @contextmanager
    def setup(self):
        if not callable(self.converter):
            raise ValueError("Converter is not callable")
        yield

    def on_input(self, value):
        value = self.converter(value)  # Put value in converter
        # And publish it.
        if value is not None and (self.output.retain or value != self.value):
            self.value = value
            self.publish()

    def publish(self):
        """ Publish the current value. """

        self.output(self.value)


class Delayer(Converter):
    """ Convert an input via an converter function and add a delay. """

    def __init__(self, *args, **kwargs):
        self.task = None
        super().__init__(*args, **kwargs)

        self.option("delay", "struct/f", "Duration of the delay in seconds")
        self.update_agent(arm=True)

    @contextmanager
    def setup(self):
        self.task = self.after(None, self.on_timeout)
        if not callable(self.converter):
            raise ValueError("Converter is not callable")
        self.task.interval = self.delay
        with super().setup():
            yield
        self.task = None

    def publish(self):
        # Start delay task if not already running.
        if not self.task:
            self.task.enable()

    def on_timeout(self):
        """ Publish value after timeout. """

        self.output(self.value)


class Toggler(Agent):
    """ Supply a bool that can be toggled. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.option("reset_value", "struct/?", "Value on start")
        self.input_topic("set", r".*", "Request a value state",
                         cb=self.on_set)
        self.input_topic("toggle", r".*", "Request to toggle",
                         cb=self.on_toggle)
        self.input_topic("condition", r"struct\/b", "Condition for output",
                         cb=self.on_condition)
        self.output_topic("output", r"struct\/?", "Output")
        self.output_topic("true_allowed", r"struct\/?",
                          "If setting to true is allowed")
        self.output_topic("false_allowed", r"struct\/?",
                          "If setting to false is allowed")
        self.output_topic("toggling_allowed", r"struct\/?",
                          "If toggling is allowed")

        self.condition = 0
        self.value = None

    @contextmanager
    def setup(self):
        # Publish initial state.
        self.publish(self.reset_value, self.condition)
        yield
        # Publish reset value and announce that no changes are allowed.
        self.publish(self.reset_value, 1 if self.reset_value else -1)

    def publish(self, new_value, new_condition):
        """ Publish all outputs according to new value and condition.

        Args:
            new_value (bool): New value to apply.
            new_condition (int): New condition to apply.
        """

        if new_value != self.value or new_condition != self.condition:
            self.toggling_allowed(new_condition == 0)
            self.false_allowed(new_condition == 0 and new_value)
            self.false_allowed(new_condition == 0 and not new_value)
        if new_condition != self.condition:
            self.condition = new_condition
        if new_value != self.value:
            self.value = new_value
            self.output(new_value)

    def on_toggle(self, _):
        """ Toggle the value if allowed. """

        if self.condition == 0:
            self.publish(not self.value, self.condition)
        else:
            self.log.debug("Toggling has been prevented by condition")

    def on_set(self, value):
        """ Request a value state explicitly. """

        if self.condition == 0:
            self.publish(value, self.condition)

    def on_condition(self, condition):
        """ Update the condition. """

        if condition != 0:
            value = condition > 0

        self.publish(value, condition)
