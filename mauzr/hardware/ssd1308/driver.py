"""
.. module:: driver
   :platform: all
   :synopsis: Driver for SSD1308 devices.

.. moduleauthor:: Alexander Sowitzki <dev@eqrx.net>
"""

import mauzr.hardware.driver

class Driver(mauzr.hardware.driver.Driver):
    """ Driver for SSD1308 devices.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units**:

        - *mqtt*
        - *i2c*

    **Configuration:**

        - *topic*: Input topic (``str``).
        - *address*: I2C address of the device (``int``).
        - *dimensions*: Tuple of display width and height (``tuple``).

    **Input topics:**

        - `topic`: Input topic containing the preformated
                   image data (``bytes``).
    """

    SET_CONTRAST = 0x81
    SET_ENTIRE_ON = 0xa4
    SET_NORM_INV = 0xa6
    SET_DISP = 0xae
    SET_MEM_ADDR = 0x20
    SET_COL_ADDR = 0x21
    SET_PAGE_ADDR = 0x22
    SET_DISP_START_LINE = 0x40
    SET_SEG_REMAP = 0xa0
    SET_MUX_RATIO = 0xa8
    SET_COM_OUT_DIR = 0xc0
    SET_DISP_OFFSET = 0xd3
    SET_COM_PIN_CFG = 0xda
    SET_DISP_CLK_DIV = 0xd5
    SET_PRECHARGE = 0xd9
    SET_VCOM_DESEL = 0xdb
    SET_CHARGE_PUMP = 0x8d

    def __init__(self, core, cfgbase="ssd1308", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        topic = cfg["topic"]
        name = "<SSD1308@{}>".format(topic)
        mauzr.hardware.driver.Driver.__init__(self, core, name)
        self._i2c = core.i2c
        self._address = cfg["address"]
        self._external_vcc = False
        self._dimensions = cfg["dimensions"]
        self._pages = cfg["dimensions"][1] // 8

        core.mqtt.subscribe(topic, self._on_frame, None, 1)

    @mauzr.hardware.driver.guard(OSError, suppress=True, ignore_ready=True)
    def _reset(self):
        # Turn display off
        self._write_cmd(Driver.SET_DISP | 0x00)

        mauzr.hardware.driver.Driver._reset(self)

    @mauzr.hardware.driver.guard(OSError, suppress=True, ignore_ready=True)
    def _init(self):
        cmds = (Driver.SET_DISP | 0x00, # off
                # address setting
                Driver.SET_MEM_ADDR, 0x00, # horizontal
                # resolution and layout
                Driver.SET_DISP_START_LINE | 0x00,
                Driver.SET_SEG_REMAP | 0x01, # column addr 127 mapped to SEG0
                Driver.SET_MUX_RATIO, self._dimensions[1] - 1,
                Driver.SET_COM_OUT_DIR | 0x08, # scan from COM[N] to COM0
                Driver.SET_DISP_OFFSET, 0x00,
                Driver.SET_COM_PIN_CFG, (0x02 if self._dimensions[1] == 32
                                         else 0x12),
                # timing and driving scheme
                Driver.SET_DISP_CLK_DIV, 0x80,
                Driver.SET_PRECHARGE, 0x22 if self._external_vcc else 0xf1,
                Driver.SET_VCOM_DESEL, 0x30, # 0.83*Vcc
                # display
                Driver.SET_CONTRAST, 0xff, # maximum
                Driver.SET_ENTIRE_ON, # output follows RAM contents
                Driver.SET_NORM_INV, # not inverted
                # charge pump
                Driver.SET_CHARGE_PUMP, 0x10 if self._external_vcc else 0x14,
                Driver.SET_DISP | 0x01
                # on
               )
        [self._write_cmd(cmd) for cmd in cmds]
        mauzr.hardware.driver.Driver._init(self)

    @mauzr.hardware.driver.guard(OSError, suppress=True, ignore_ready=True)
    def _on_frame(self, _topic, frame):
        x0 = 0
        x1 = self._dimensions[0] - 1
        if self._dimensions[0] == 64:
            # displays with width of 64 pixels are shifted by 32
            x0 += 32
            x1 += 32
        self._write_cmd(Driver.SET_COL_ADDR)
        self._write_cmd(x0)
        self._write_cmd(x1)
        self._write_cmd(Driver.SET_PAGE_ADDR)
        self._write_cmd(0)
        self._write_cmd(self._pages - 1)
        self._i2c.write(self._address, frame)

    def _write_cmd(self, cmd):
        self._i2c.write(self._address, (0x80, cmd))
