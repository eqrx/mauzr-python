""" PCA9685 controller. """

import mauzr
import mauzr.hardware.controller
from mauzr.serializer import Struct
from mauzr.hardware.controller import TimedPublisher

__author__ = "Alexander Sowitzki"


class Controller(TimedPublisher):
    """ Controller for PCA9685 PWM devices.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units**:

        - *mqtt*
    """

    def __init__(self, core, cfgbase="pca9685", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)
        self._cfg = cfg
        self._mqtt = core.mqtt
        self._old_values = None
        self._values = [0] * 16
        self._mapping = {}

        self._mqtt.setup_publish(cfg["topic"], Struct("!" + "H" * 16))

        ser = Struct("!H")
        for pin, subcfg in cfg["pins"].items():
            m = {"pin": pin, "mapper": angle_mapper(*(subcfg["angles"] +
                                                      subcfg["pwms"]))}
            self._mapping[subcfg["topic"]] = m
            self._mqtt.subscribe(subcfg["topic"], self._on_angle, ser, 0)

        name = "<PCA9685@{}>".format(cfg["topic"])
        TimedPublisher.__init__(self, core, name, cfg["interval"])

    @mauzr.hardware.driver.guard(OSError, suppress=True)
    def _on_angle(self, topic, angle):
        m = self._mapping[topic]
        m["pin"] = m["mapper"](angle)

    def _publish(self):
        if self._values != self._old_values:
            self._mqtt.publish(self._cfg["topic"], self._values, True)
            self._old_values = list(self._values)


def angle_mapper(angle_min, angle_max, pwm_min, pwm_max):
    """ Create PWM mapper funtion for angles.

    :param angle_min: Lower angle border.
    :type angle_min: float
    :param angle_max: Upper angle border.
    :type angle_max: float
    :param pwm_min: Lower PWM border.
    :type pwm_min: int
    :param pwm_max: Upper PWM border.
    :type pwm_max: int
    :returns: Function that accepts an angle in degrees and \
              returns the PWM value.
    :rtype: callable
    """

    angle_multiplier = (pwm_max - pwm_min) / (angle_max - angle_min)

    def _map(angle):
        angle = max(angle_min, min(angle_max, angle)) - angle_min
        return int(angle_multiplier * angle) + pwm_min

    return _map


def main():
    """ Entry point. """

    mauzr.cpython("mauzr", "pca9685controller", Controller)
