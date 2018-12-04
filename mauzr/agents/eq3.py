from contextlib import contextmanager
import eq3bt
import bluepy.btle
from mauzr import Agent, PollMixin

__author__ = "Alexander Sowitzki"

class Driver(PollMixin, Agent):
    """ Driver for EQ3 thermostats. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.output_topic("valve", r"struct\/B", "Current value state")
        self.input_topic("target", r"struct\/\!f", "Target temperature")

        self.option("mac", "str", "MAC address of the thermostat")
        self.thermostat = None
        self.update_agent(arm=True)

    @contextmanager
    def setup(self):
        self.thermostat = eq3bt.Thermostat(self.mac)
        yield
        self.thermostat = None

    def poll(self):
        """ Poll the valve state. """

        try:
            self.thermostat.update()
        except bluepy.btle.BTLEException:
            pass
        else:
            self.valve(self.thermostat.valve_state)

    def on_input(self, target):
        self.thermostat.target_temperature = target
        try:
            self.thermostat.update()
        except bluepy.btle.BTLEException:
            pass
