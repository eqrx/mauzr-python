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
        self.option("device_name", "str", "Light name")

        self.update_agent(arm=True)

    @contextmanager
    def setup(self):
        self.api = APIFactory(host=self.host,
                              psk_id=self.identity, psk=self.psk).request
        devices = self.api(self.api(Gateway().get_devices()))
        lights = [dev for dev in devices
                  if dev.has_light_control and dev.name == self.device_name]
        if len(lights) != 1:
            raise ValueError("Light unknown")
        self.light = lights[0]

        yield
        self.api = None


class TemperatureSettable(Light):
    """ Controller the light temperature of IKEA tradfri lights. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.input_topic("temperature", r"struct/B", "Color temperature",
                         cb=self.temperature)

    def temperature(self, value):
        """ Set temperature value. """

        value = min(value+250, 454)
        self.api(self.light.light_control.set_color_temp(value))


class IntensitySettable(Light):
    """ Controller the intensity of IKEA tradfri lights. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.input_topic("intensity", r"struct/B", "Dimmer setting",
                         cb=self.intensity)

    def intensity(self, value):
        """ Set dimm value. """

        value = min(value, 254)
        self.api(self.light.light_control.set_dimmer(value))


class TemperatureLight(TemperatureSettable, IntensitySettable):
    """ IKEA tradfri light that support dimm and temperature setting. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_agent(arm=True)
