""" Controller for Trellis devices. """
__author__ = "Alexander Sowitzki"

import mauzr.platform.serializer

class Controller:
    """ Driver for trellis devices.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units**:

        - mqtt

    **Configuration:**

        - **base** (:class:`str`) - Topic base.
        - **button_topics** (:class:`tuple`)  - List of topics to map button \
                                                presses to.
        - **led_topics** (:class:`tuple`)  - List of topics to receive led \
                                             settings by.

    **Input topics:**

        - **/buttons** - Button readout from the chip.
        - **[** ``led_topics`` **]** (``?``) - Topics to be bound to the LEDs.

    **Output topics:**

        - **leds**: Preformated LED data.
        - **[** ``button_topics`` **]** (``?``) - Topics to be bound to \
                                                  the buttons.
    """

    LED_LUT = [0x3a, 0x37, 0x35, 0x34,
               0x28, 0x29, 0x23, 0x24,
               0x16, 0x1b, 0x11, 0x10,
               0x0e, 0x0d, 0x0c, 0x02]

    BUTTON_LUT = [0x07, 0x04, 0x02, 0x22,
                  0x05, 0x06, 0x00, 0x01,
                  0x03, 0x10, 0x30, 0x21,
                  0x13, 0x12, 0x11, 0x31]

    def __init__(self, core, cfgbase="trellis", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._base = cfg["base"]
        self._button_topics = cfg["button_topics"]
        self._led_topics = cfg["led_topics"]
        if len(self._button_topics) != 16 or len(self._led_topics) != 16:
            raise ValueError("16 topics for each leds and buttons needed.")

        self._mqtt = core.mqtt
        self._button_values = [None] * 16
        self._led_values = [False] * 16
        core.mqtt.setup_publish(self._base + "leds", None, 0)
        core.mqtt.subscribe(self._base + "buttons", self._on_buttons, None, 0)
        [core.mqtt.subscribe(topic, self._on_led,
                             mauzr.platform.serializer.Bool, 0)
         for topic in self._led_topics if topic is not None]
        [core.mqtt.setup_publish(topic, mauzr.platform.serializer.Bool, 0)
         for topic in self._button_topics if topic is not None]
        self._publish()

    def _on_buttons(self, _topic, buttons):
        for topic, i, lutv in zip(self._button_topics, range(0, 16),
                                  Controller.BUTTON_LUT):
            if topic is None:
                continue
            value = (buttons[lutv >> 4] & (1 << (lutv & 0xf))) > 0

            # Avoid redundancy only when sending
            if value != self._button_values[i]:
                self._button_values[i] = value
                self._mqtt.publish(topic, value, True)

    def _on_led(self, topic, val):
        changed = False
        for i in range(0, 16):
            if topic == self._led_topics[i]:
                if self._led_values[i] != val:
                    self._led_values[i] = val
                    changed = True
        if changed:
            self._publish()

    def _publish(self):
        buf = [0] * 8
        for i, value in zip(range(0, 16), self._led_values):
            entry = 1 << (Controller.LED_LUT[i] & 0xf)
            if value:
                buf[Controller.LED_LUT[i] >> 4] |= entry
            else:
                buf[Controller.LED_LUT[i] >> 4] &= ~entry

        data = [0]
        for entry in buf:
            data.append(entry & 0xff)
            data.append(entry >> 8)

        self._mqtt.publish(self._base + "leds", bytes(data), True)
