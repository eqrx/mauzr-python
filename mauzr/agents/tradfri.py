""" Driver for IKEA tradfri devices. """

from contextlib import contextmanager
from pytradfri.api.libcoap_api import APIFactory
from pytradfri import Gateway
from mauzr import Agent

__author__ = "Alexander Sowitzki"


class Light(Agent):
    """ Abstract agent for IKEA trafdri lights. """

    def __init__(self, *args, **kwargs):
        self.api, self.light = None, None
        super().__init__(*args, **kwargs)

        self.option("host", "str", "Gateway hostname")
        self.option("psk", "str", "Gateway access key")
        self.option("identity", "str", "Gateway access identity")
        self.option("index", "struct/B", "Light index")

        self.update_agent(arm=True)

    @contextmanager
    def setup(self):
        self.api = APIFactory(host=self.host,
                              psk_id=self.identity, psk=self.psk).request
        devices = self.api(self.api(Gateway().get_devices()))
        lights = [dev for dev in devices if dev.has_light_control]
        self.light = lights[self.index]

        yield
        self.api = None


class DimmableLight(Light):
    """ Controller agent for IKEA tradfri dimmable lights. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.input_topic("input", r"struct/B", "Dimmer setting")
        self.update_agent(arm=True)

    def on_input(self, value):
        """ Set dimm value. """

        value = min(value, 254)

        self.api(self.light.light_control.set_dimmer(value))
