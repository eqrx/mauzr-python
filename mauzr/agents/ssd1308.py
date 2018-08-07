""" Driver for SSD1308 devices. """

from contextlib import contextmanager
from mauzr import Agent, I2CMixin

__author__ = "Alexander Sowitzki"


class LowDriver(Agent, I2CMixin):
    """ Talk to a SSD1308 controlled display and send image frames to it.

    Raw image data is received by the high level driver. Communication is
    done via i2c.
    """

    def __init__(self, *args, **kwargs):
        self.pre, self.dim, self.frame_len = None, None, None
        super().__init__(*args, **kwargs)

        self.option("dimensions", "struct/!HH", "Width and height of display",
                    cb=self.on_dimensions)
        self.input_topic("frame", r"bytes/\d+", "Raw image frame")

        self.update_agent(arm=True)

    def on_dimensions(self, dim):
        """ Receive display dimensions and prepare controller for it.

        Args:
            dim (tuple): Width and height of the display.
        """

        # Create pre frame commands
        x0, x1 = 0, dim[0] - 1
        if dim == 64:
            # 64 width displays are shifted
            x0 += 32
            x1 += 32
        self.pre = (0x21, x0, x1, 0x22, 0, dim[1] // 8)

        # Remember dimensions.
        self.frame_len = dim[0]*dim[1]//8+1
        self.dim = dim

    @contextmanager
    def setup(self):
        """ Context manager for hardware. """

        cmds = (0xae | 0x00, 0x20, 0x00, 0x40 | 0x00, 0xa0 | 0x01,
                0xa8, self.dim[1] - 1, 0xc0 | 0x08, 0xd3, 0x00,
                0xda, (0x02 if self.dim[1] == 32 else 0x12),
                0xd5, 0x80, 0xd9, 0xf1, 0xdb, 0x30, 0x81, 0xff, 0xa4, 0xa6,
                0x8d, 0x14, 0xae | 0x01)
        [self.write_cmd(cmd) for cmd in cmds]

        yield

        # Turn display off
        self.write_cmd(0xae | 0x00)

    def on_input(self, frame):
        """ Receive raw image data and send it to the display.

        Args:
            frame (bytes): Raw frame data. This data is expected to be \
                           prepended with the data command byte (0x40)
        Raises:
            ValueError: If frame size is invalid.
        """

        if len(frame) != self.frame_len:
            raise ValueError("Expected frame length {self.frame_len}, "\
                             "got {len(frame)}")

        [self.write_cmd(c) for c in self.pre]  # Write pilot commands.
        self.i2c.write(frame)  # Write actual data.

    def _write_cmd(self, cmd):
        """ Send a command to chip.

        Args:
            cmd (int): Single command byte.
        """

        self.i2c.write((0x80, cmd))


class HighDriver(Agent):
    """ High level driver that converts images to raw data for low level driver.

    Image data needs to be shifted.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.input_topic("input", r"image\/.+", "Image input")
        self.input_topic("output", r"bytes\/\d+", "Raw image output")
        self.update_agent(arm=True)

    def on_input(self, image):
        # Get image dimensions
        height, width = image.shape[:2]
        # Number of data pages
        pages = height // 8
        # Create buffer
        buf = [0]*(width*pages+1)
        # First byte is data command
        buf[0] = 0x40
        # Iterate through the memory pages
        index = 1
        for page in range(pages):
            for x in range(width):
                bits = 0
                for bit in [0, 1, 2, 3, 4, 5, 6, 7]:
                    bits = bits << 1
                    bits |= 0 if image[x, page*8+7-bit] == 0 else 1
                # Update buffer byte and increment to next byte.
                buf[index] = bits
                index += 1

        self.output(bytes(buf))
