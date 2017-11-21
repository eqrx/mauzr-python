""" Access GPIO via Sysfs. """
__author__ = "Alexander Sowitzki"

# pylint: disable = no-member,import-error
import RPi.GPIO as GPIO


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
        self._pins = {}
        self.listeners = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_details):
        GPIO.cleanup()

    def setup_input(self, name, edge, pullup):
        """ Set pin as input.

        :param name: ID of the pin.
        :type name: str
        :param edge: Edges to inform listeners about. May be "none", "rising", \
                     "falling" or "both".
        :type edge: str
        :param pullup: Pull mode of the pin. May be "none", "up" or "down".
        :type pullup: str
        """

        GPIO.setup(name, GPIO.IN, pull_up_down=self.PULL_MAPPING[pullup])

        if edge != "none":
            GPIO.add_event_detect(name, self.EDGE_MAPPING[edge],
                                  callback=self._on_change)

        self._pins[name] = {"name": name, "type": "in"}

    def _on_change(self, name):
        value = self[name]
        [l(name, value) for l in self.listeners]

    def setup_output(self, name, pwm=False, initial=False):
        """ Set pin as output.

        :param name: Numer of the pin.
        :type name: int
        :param pwm: If value if PWM.
        :type pwm: bool
        :param initial: Initial value to set.
        :type initial: bool
        """

        if pwm:
            pwm = GPIO.PWM(name, 140)
            pwm.start()
        else:
            GPIO.setup(name, GPIO.OUT)
        self._pins[name] = {"name": name, "type": "out", "pwm": pwm}
        self[name] = initial

    def __getitem__(self, name):
        # Retrieve value of an input pin.

        return GPIO.input(name)

    def __setitem__(self, name, value):
        # Set the value of an output pin.

        if self._pins[name].get("pwm", None):
            self._pins[name]["pwm"].ChangeDutyCycle(value)
        else:
            GPIO.output(name, value)
