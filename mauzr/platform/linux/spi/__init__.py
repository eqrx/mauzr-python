""" Provide I2C functionality for linux. """

import fcntl
import io
from ctypes import create_string_buffer
from . import _types

__author__ = "Alexander Sowitzki"


class Device:
    """ Manage an I2C bus.

    :param core: Core instance.
    :type core: object
    :param path: Path to the device file.
    :type path: str
    :param address: Address of the device.
    :type address: int
    :param speed: Transfer speed in Hz.
    :type speed: int
    """

    def __init__(self, core, path, address, speed):
        self.path = path
        self.address = address
        self.speed = speed
        self.fd = None
        core.add_context(self)

    def __enter__(self):
        # Open the bus file.

        self.fd = io.open(self.path, "r+b", buffering=0)
        return self

    def __exit__(self, *exc_details):
        # Close the bus file.
        self.fd.close()

    def transfer(self, data):
        """ Send and receive data

        :param data: Date to send
        :type data: bytes
        :returns: Received data
        :rtype: bytes
        """

        if not isinstance(data, bytes):
            data = bytes(data)

        buf = create_string_buffer(data)
        msg = _types.IoctlData(tx_buf=buf, rx_buf=buf,
                               len=len(data), speed_hz=self.speed)

        fcntl.ioctl(self.fd, _types.SPI_IOC_MESSAGE, msg)

        return buf
