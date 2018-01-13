""" Driver for tsl2561 devices. """

from mauzr.hardware.driver import DelayedPollingDriver
import mauzr.serializer

__author__ = "Alexander Sowitzki"


class Driver(DelayedPollingDriver):
    """ Driver for tsl2561 devices.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict
    """

    def __init__(self, core, cfgbase="tsl2561", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._i2c = core.i2c
        self._mqtt = core.mqtt
        self._address = cfg["address"]
        self._base = cfg["base"]

        core.mqtt.setup_publish(self._base + "channels",
                                mauzr.serializer.Struct("<HH"), 0)

        DelayedPollingDriver.__init__(self, core, self._base, "TSL2561",
                                      30000, 500, init_delay=3000)

    @mauzr.hardware.driver.guard(OSError, suppress=True, ignore_ready=True)
    def _init(self):
        self._on(True)
        self._i2c.write(self._address, [0x81, 2])
        self._on(False)

        super()._init()

    def _on(self, value):
        self._i2c.write(self._address, [0x80, 3 if value else 0])

    @mauzr.hardware.driver.guard(OSError, suppress=True)
    def _poll(self):
        """ Start a fetch. """

        self._on(True)

    @mauzr.hardware.driver.guard(OSError, suppress=True)
    def _receive(self):
        """ Called when a fetch is finished. """

        broadband = self._i2c.read_register(self._address, 0xac, fmt="<H")
        ir = self._i2c.read_register(self._address, 0xae, fmt="<H")
        self._on(False)
        self._mqtt.publish(self._base + "channels", (broadband, ir), True)
