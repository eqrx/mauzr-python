#!/usr/bin/python3
"""
.. module:: converter
   :platform: all
   :synopsis: Converter for SSD1308 devices.

.. moduleauthor:: Alexander Sowitzki <dev@eqrx.net>
"""

from mauzr.util.image.serializer import Pillow as ImageSerializer
import mauzr.hardware.controller

class Converter(mauzr.hardware.controller.TimedPublisher):
    """ Convert images of a topic to command bytes for SSD1308 display.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units**:

        - *mqtt*

    **Configuration:**

        - *input*: Input topic (``str``).
        - *output*: Output topic (``str``).
        - *interval*: Output frequency in milliseconds (``int``).

    **Input topics:**

        - `input`: Input topic containing a bitmap image (``bytes``).

    **Output topics:**

        - `output`: Output topic containing the preformated data (``bytes``).
    """

    def __init__(self, core, cfgbase="ssd1308", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._out_topic = cfg["out"]
        name = "<SSD1308Converter@{}>".format(self._out_topic)
        mauzr.hardware.controller.TimedPublisher.__init__(self, core, name,
                                                          cfg["interval"])

        core.mqtt.subscribe(cfg["in"], self._on_input,
                            ImageSerializer("bmp"), 0)
        core.mqtt.setup_publish(self._out_topic, None, 0)
        self._buf = None
        self._mqtt = core.mqtt

    def _publish(self):
        # Check if new image present
        if self._buf is not None:
            self._mqtt.publish(self._out_topic, bytes(self._buf), True)
            self._buf = None

    def _on_input(self, _topic, image):
        # Get image dimensions
        imwidth, imheight = image.size
        # Number of data pages
        pages = imheight // 8
        # Create buffer
        buf = [0]*(imwidth*pages+1)
        # First byte is data command
        buf[0] = 0x40
        # Get pixels from image
        pix = image.load()
        # Iterate through the memory pages
        index = 1
        for page in range(pages):
            for x in range(imwidth):
                bits = 0
                for bit in [0, 1, 2, 3, 4, 5, 6, 7]:
                    bits = bits << 1
                    bits |= 0 if pix[(x, page*8+7-bit)] == 0 else 1
                # Update buffer byte and increment to next byte.
                buf[index] = bits
                index += 1
        self._buf = buf

def main():
    """ Main method for the Converter. """
    # Setup core
    core = mauzr.linux("mauzr", "ssd1308converter")
    # Setup MQTT
    core.setup_mqtt()
    # Spin up converter
    Converter(core)
    # Run core
    core.run()

if __name__ == "__main__":
    main()
