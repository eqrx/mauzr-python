""" Provide SPI functionality. """


import array
import fcntl
import ctypes
from contextlib import contextmanager

__author__ = "Alexander Sowitzki"


class IoctlData(ctypes.Structure):
    """ Ioctl message for spi transfer. See linux spi doc. """

    _fields_ = [('tx_buf', ctypes.c_ulonglong),
                ('rx_buf', ctypes.c_ulonglong),
                ('len', ctypes.c_uint),
                ('speed_hz', ctypes.c_uint),
                ('delay_usecs', ctypes.c_ushort),
                ('bits_per_word', ctypes.c_ubyte),
                ('cs_change', ctypes.c_ubyte),
                ('tx_nbits', ctypes.c_ubyte),
                ('rx_nbits', ctypes.c_ubyte),
                ('pad', ctypes.c_ushort)]



class Bus:  # pragma: no cover
    """ Manage an SPI bus. """

    def __init__(self, path, speed):
        self.path = path
        self.speed = speed
        self.fd = None

    def __enter__(self):
        self.fd = open(self.path, "r+b", buffering=0)
        return self

    def __exit__(self, *exc_details):
        self.fd.close()
        self.fd = None

    def transfer(self, data):
        """ Transfer data to/from device.

        Args:
            data (bytes): Bytes transfered to the device.
        Returns:
            bytes: Data read from device.
        """

        if not isinstance(data, bytes):
            # Try casting to bytes if data is list of ints or bytearray.
            data = bytes(data)


        buf = array.array('B', data) # Convert to c buffer
        buf_addr, buf_len = buf.buffer_info()

        # Prepare ioctl parameter.
        msg = IoctlData(tx_buf=buf_addr, rx_buf=buf_addr,
                        len=buf_len, speed_hz=self.speed)

        # Perform SPI operation.
        fcntl.ioctl(self.fd, 0x40206b00, msg)

        return buf

class SPIMixin:  # pragma: no cover
    """ Provide an reference to an SPI bus. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.spi = None
        self.option("spi_path", "str", "SPI device path")
        self.option("spi_speed", "struct/!I", "SPI speed")

        self.add_context(self.__spi_context)

    @contextmanager
    def __spi_context(self):
        # Get Handle for the given device.

        with Bus(self.spi_path, self.spi_speed) as spi:
            self.spi = spi
            yield
            self.spi = None
