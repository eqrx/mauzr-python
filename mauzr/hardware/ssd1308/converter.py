#!/usr/bin/python3
"""
.. module:: converter
   :platform: all
   :synopsis: Converter for SSD1308 devices.

.. moduleauthor:: Alexander Sowitzki <dev@eqrx.net>
"""

import mauzr
from mauzr.util.image.serializer import Pillow as ImageSerializer

def converter(core, cfgbase="ssd1308", **kwargs):
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

        - *in*: Input topic (``str``).
        - *out*: Output topic (``str``).

    **Input topics:**

        - `in`: Input topic containing a bitmap image (``bytes``).

    **Output topics:**

        - `out`: Output topic containing the preformated data (``bytes``).
    """

    cfg = core.config[cfgbase]
    cfg.update(kwargs)
    mqtt = core.mqtt
    mqtt.setup_publish(cfg["out"], None, 0)

    def _on_input(_topic, image):
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
        mqtt.publish(cfg["out"], bytes(buf), True)
    mqtt.subscribe(cfg["in"], _on_input, ImageSerializer("bmp"), 0)

def main():
    """ Main method for the converter. """
    # Setup core
    core = mauzr.cpython("mauzr", "ssd1308converter")
    # Setup MQTT
    core.setup_mqtt()
    # Spin up converter
    converter(core)
    # Run core
    core.run()

if __name__ == "__main__":
    main()
