""" Access GPIO via Sysfs. """

import RPi.GPIO as GPIO  # pylint: disable = no-member,import-error

__author__ = "Alexander Sowitzki"


class Pins:
    """ Use GPIO pins on raspberry. """

    PULL_MAPPING = {"none": GPIO.PUD_OFF,
                    "down": GPIO.PUD_DOWN,
                    "up": GPIO.PUD_UP}
    EDGE_MAPPING = {"rising": GPIO.RISING,
                    "falling": GPIO.FALLING,
                    "both": GPIO.BOTH}

    def __init__(self, core, cfgbase="gpio", **kwargs):
        GPIO.setmode(GPIO.BCM)
        cfg = core.config[cfgbase]
        cfg.update(kwargs)
        core.add_context(self)
        self._inputs = {}
        self._outputs = {}
        self.listeners = []
        self._task = core.scheduler(self._poll, 50, single=False).enable()

    def __enter__(self):
        return self

    def __exit__(self, *exc_details):
        GPIO.cleanup()

    def setup_input(self, name, _edge, pullup):
        """ Set pin as input.

        :param name: ID of the pin.
        :type name: str
        :param _edge: Edges to inform listeners about. May be "none", \
                     "rising", "falling" or "both".
        :type _edge: str
        :param pullup: Pull mode of the pin. May be "none", "up" or "down".
        :type pullup: str
        """

        GPIO.setup(name, GPIO.IN, pull_up_down=self.PULL_MAPPING[pullup])

        self._inputs[name] = {"name": name, "value": None}

    def setup_output(self, name, pwm=False, initial=False):
        """ Set pin as output.

        :param name: Numer of the pin.
        :type name: int
        :param pwm: If value if PWM.
        :type pwm: bool
        :param initial: Initial value to set.
        :type initial: bool
        """

        self._outputs[name] = {"name": name, "pwm": None}

        GPIO.setup(name, GPIO.OUT)
        if pwm:
            pwm = GPIO.PWM(name, 200)
            pwm.start(initial * 100.0)
            self._outputs[name]["pwm"] = pwm
        else:
            self[name] = initial

    def _poll(self):
        for pin in self._inputs.values():
            name = pin["name"]
            value = self[name]
            if value != pin["value"]:
                pin["value"] = value
                [l(name, value) for l in self.listeners]

    def __getitem__(self, name):
        # Retrieve value of an input pin.

        return GPIO.input(name)

    def __setitem__(self, name, value):
        # Set the value of an output pin.

        if self._outputs[name]["pwm"] is not None:
            self._outputs[name]["pwm"].ChangeDutyCycle(value * 100.0)
        else:
            GPIO.output(name, value)
