""" Driver for tsl2561 devices. """
__author__ = "Alexander Sowitzki"


import mauzr.hardware.driver
import mauzr.serializer

class Driver(mauzr.hardware.driver.DelayedPollingDriver):
    """ Driver for tsl2561 devices.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Configuration:**

        - **base** (:class:`str`) - Base for topics.
        - **address** (:class:`int`) - I2C address of the device.
        - **interval** (:class:`int`) - Output frequency in milliseconds.

    **Output topics:**

        - **/illuminance** (``!f``) - Current illuminance in lumen.
    """

    def __init__(self, core, cfgbase="tsl2561", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._address = cfg["address"]
        self._base = cfg["base"]
        name = "<TSL2561@{}>".format(self._base)

        self._i2c = core.i2c
        self._mqtt = core.mqtt

        core.mqtt.setup_publish(self._base + "illuminance",
                                mauzr.serializer.Struct("!f"), 0)

        mauzr.hardware.driver.DelayedPollingDriver.__init__(self, core, name,
                                                            cfg["interval"],
                                                            500,
                                                            init_delay=3000)

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
        self._receive_task.enable()

    @mauzr.hardware.driver.guard(OSError, suppress=True)
    def _receive(self):
        """ Called when a fetch is finished. """

        broadband = self._i2c.read_register(self._address, 0xac, fmt="<H")
        ir = self._i2c.read_register(self._address, 0xae, fmt="<H")
        self._on(False)
        lux = self._calculate_lux(broadband, ir)
        self._mqtt.publish(self._base + "illuminance", lux, True)

    @staticmethod
    def _calculate_lux(broadband, ir):
        """ Calculate the lux value from a measurement.

        :param broadband: Broadband measurement.
        :type broadband: int
        :param ir: Infrared measurement.
        :type ir: int
        :returns: Lux value.
        :rtype: int
        :raises mauzr.hardware.driver.DriverError: If sensor is oversaturated.
        """

        channels = [broadband, ir]

        if True in [ch > 65000 for ch in channels]:
            raise mauzr.hardware.driver.DriverError('Sensor is saturated')

        channels = [ch * 16 for ch in channels]

        ratio = 0 if not channels[0] else int(channels[1] * 1024 / channels[0])
        ratio = (ratio + 1) >> 1

        if ratio >= 0 and ratio <= 0x40:
            f = (0x01f2, 0x01be)
        elif ratio <= 0x80:
            f = (0x214, 0x2d1)
        elif ratio <= 0x00c0:
            f = (0x23f, 0x37b)
        elif ratio <= 0x0100:
            f = (0x270, 0x3fe)
        elif ratio <= 0x0138:
            f = (0x16f, 0x1fc)
        elif ratio <= 0x019a:
            f = (0xd2, 0xfb)
        elif ratio <= 0x29a:
            f = (0x18, 0x12)
        else:
            f = (0, 0)

        channels = [ch * fi for ch, fi in zip(channels, f)]
        return (max(0, channels[0] - channels[1]) + 8192) >> 14
