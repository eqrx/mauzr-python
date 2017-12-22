""" Driver for Trellis devices. """
__author__ = "Alexander Sowitzki"


import mauzr.hardware.driver

class Driver(mauzr.hardware.driver.PollingDriver):
    """ Driver for trellis devices.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units**:

        - mqtt
        - i2c

    **Configuration:**

        - **base** (:class:`str`) - Base to use for topics.
        - **address** (:class:`int`) - I2C address of the device.
        - **interval** (:class:`int`) - Button poll intervall in milliseconds.
        - **interrupt** (:class:`str`) - Pin to use as input interrupt
        - **brightness** (:class:`int`) - Brightness of all active LEDs, 0-15.

    **Input topics:**

        - **/leds** (:class:`bytes`) - Preformated LED data.

    **Output topics:**

        - **/buttons** (:class:`bytes`) - Button readout from the chip.
    """

    def __init__(self, core, cfgbase="trellis", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._base = cfg["base"]

        name = "<Trellis@{}>".format(self._base)
        mauzr.hardware.driver.PollingDriver.__init__(self, core, self._base,
                                                     name, cfg["interval"])
        self._i2c = core.i2c
        self._address = cfg["address"]
        self._keys = None
        self._lastkeys = None

        self._interrupt = cfg.get("interrupt", None)
        if self._interrupt is not None:
            core.gpio.setup_input(self._interrupt, "falling", "none")
            core.gpio.listeners.append(self._on_pin)

        self._mqtt = core.mqtt
        self._bs = cfg["brightness"]
        core.mqtt.setup_publish(self._base + "buttons", None, 0)
        core.mqtt.subscribe(self._base + "leds", self._on_message, None, 0)

    def _on_pin(self, name, value):
        if name == self._interrupt:
            self._poll()

    @mauzr.hardware.driver.guard(OSError, suppress=True, ignore_ready=True)
    def _init(self):
        # Turn on the oscillator.
        self._i2c.write(self._address, [0x21])
        # No blinking
        self._i2c.write(self._address, [0x81])
        # Max brightness.
        self._brightness(self._bs)
        # Turn on interrupt, active high.
        self._i2c.write(self._address, [0xa1])

        super()._init()

    @mauzr.hardware.driver.guard(OSError, suppress=True, ignore_ready=True)
    def _reset(self):
        self._i2c.write(self._address, [0] * 33)
        super()._reset()

    def _brightness(self, brightness):
        brightness = max(0, min(brightness, 15))
        self._i2c.write(self._address, [0xe0 | brightness])

    @mauzr.hardware.driver.guard(OSError, suppress=True)
    def _poll(self):
        self._lastkeys = self._keys
        self._keys = self._i2c.read_register(self._address, 0x40, 6)
        if self._keys != self._lastkeys:
            self._mqtt.publish(self._base + "buttons", self._keys, True)

    @mauzr.hardware.driver.guard(OSError, suppress=True)
    def _on_message(self, _topic, values):
        self._i2c.write(self._address, values)
