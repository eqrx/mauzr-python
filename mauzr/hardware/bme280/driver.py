""" Driver for BME280 devices. """
__author__ = "Alexander Sowitzki"

import mauzr
from  mauzr.hardware.driver import DelayedPollingDriver
from mauzr.serializer import Struct

# pylint: disable=too-many-instance-attributes
class Driver(DelayedPollingDriver):
    """ Driver for BME280 devices.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict
    """

    def __init__(self, core, cfgbase="bme280", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._address = cfg["address"]
        self._base = cfg["base"]
        self._i2c = core.i2c

        DelayedPollingDriver.__init__(self, core, self._base, "BME280",
                                      30000, 12000)

        self._mqtt.setup_publish(self._base + "calibrations/pt",
                                 Struct("<HhhHhhhhhhhhBB"), 0)
        self._mqtt.setup_publish(self._base + "calibrations/h", None, 0)
        self._mqtt.setup_publish(self._base + "readout", None, 0)

    @mauzr.hardware.driver.guard(OSError, suppress=True, ignore_ready=True)
    def _init(self):
        pt_calibrations = self._i2c.read_register(self._address, 0x88,
                                                  fmt="<HhhHhhhhhhhhBB")
        h_calibration = self._i2c.read_register(self._address, 0xE1, amount=7)
        self._mqtt.publish(self._base + "calibrations/pt",
                           pt_calibrations, True)
        self._mqtt.publish(self._base + "calibrations/h", h_calibration, True)
        self._i2c.write(self._address, [0xf4, 0x3f])
        super()._init()

    @mauzr.hardware.driver.guard(OSError, suppress=True)
    def _poll(self):
        """ Begin reading a new sample. """

        self._i2c.write(self._address, [0xf2, 1])
        self._i2c.write(self._address, [0xf4, 0x25])
        self._receive_task.enable()

    @mauzr.hardware.driver.guard(OSError, suppress=True)
    def _receive(self):
        """ Finalize reading and publish readout. """

        readout = self._i2c.read_register(self._address, 0xf7, amount=8)
        self._mqtt.publish(self._base + "readout", readout, True)
