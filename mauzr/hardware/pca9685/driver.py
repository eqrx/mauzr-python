""" PCA9685 driver. """

import time
import mauzr
import mauzr.hardware.driver
from mauzr.serializer import Struct

__author__ = "Alexander Sowitzki"


class Driver(mauzr.hardware.driver.Driver):
    """ Driver for PCA9685 PWM devices.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units**:

        - *mqtt*
        - *i2c*
    """

    MODE1 = 0x00
    MODE2 = 0x01
    LED0_ON_L = 0x06
    LED0_ON_H = 0x07
    LED0_OFF_L = 0x08
    LED0_OFF_H = 0x09
    SLEEP = 0x10
    ALLCALL = 0x01
    OUTDRV = 0x04

    def __init__(self, core, cfgbase="pca9685", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)
        self._i2c = core.i2c
        self._address = cfg["address"]

        name = "<PCA9685@{}>".format(cfg["topic"])
        mauzr.hardware.driver.Driver.__init__(self, core, name)
        core.mqtt.subscribe(cfg["topic"], self._on_angle,
                            Struct("!" + "H" * 16), 0)

    @mauzr.hardware.driver.guard(OSError, suppress=True, ignore_ready=True)
    def _init(self):
        self._i2c.write(self._address, [Driver.MODE2, Driver.OUTDRV])
        self._i2c.write(self._address, [Driver.MODE1, Driver.ALLCALL])
        time.sleep(0.005)  # wait for oscillator
        mode1 = self._i2c.read_register(self._address, Driver.MODE1, fmt="B")
        mode1 = mode1 & ~Driver.SLEEP  # wake up (reset sleep)
        self._i2c.write(self._address, [Driver.MODE1, mode1])
        time.sleep(0.005)  # wait for oscillator
        mauzr.hardware.driver.Driver._init(self)

    def _set_pwm(self, ch, on, off):
        # Set a single PWM.

        self._i2c.write(self._address, [Driver.LED0_ON_L+4*ch, on & 0xff])
        self._i2c.write(self._address, [Driver.LED0_ON_H+4*ch, on >> 8])
        self._i2c.write(self._address, [Driver.LED0_OFF_L+4*ch, off & 0xff])
        self._i2c.write(self._address, [Driver.LED0_OFF_H+4*ch, off >> 8])

    @mauzr.hardware.driver.guard(OSError, suppress=True)
    def _on_angle(self, _topic, pwms):
        for pin, pwm in zip(range(0, 16), pwms):
            self._set_pwm(pin, 0, pwm)
