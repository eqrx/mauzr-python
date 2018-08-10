""" Provide I2C functionality for linux. """

import fcntl
import io
import os
import struct
import ctypes
from ctypes import create_string_buffer
from contextlib import contextmanager

__author__ = "Alexander Sowitzki"


class Message(ctypes.Structure):
    """ Represent the struct i2c_msg from linux/i2c-dev.h. """

    _fields_ = [('addr', ctypes.c_uint16),
                ('flags', ctypes.c_ushort),
                ('len', ctypes.c_short),
                ('buf', ctypes.POINTER(ctypes.c_char))]

    __slots__ = [name for name, type in _fields_]


class IoctlData(ctypes.Structure):
    """ Represent the struct i2c_rdwr_ioctl_data from linux/i2c-dev.h. """

    _fields_ = [('msgs', ctypes.POINTER(Message)),
                ('nmsgs', ctypes.c_int)]

    __slots__ = [name for name, type in _fields_]

I2C_M_RD = 0x0001
I2C_SLAVE = 0x0703
I2C_RDWR = 0x0707

__author__ = "Alexander Sowitzki"


class Device:  # pragma: no cover
    """ Handle used to communicate with a device behind an I2C bus.

    Args:
        path (str): I2C Device path.
        address (int): Address of the device.
    """

    READ_ACTION = 0
    """ Indicate a read action in a transaction. """

    WRITE_ACTION = 1
    """ Indicate a write action in a transaction. """

    def __init__(self, path, address):
        self.path = path
        self.address = address
        self.fd = None

    def write(self, data):
        """ Write data to a device.

        Args:
            data (bytes): Data to write.
        """

        if isinstance(data, (tuple, list)):
            data = bytes(data)
        self.fd.write(data)

    def read(self, amount=None, fmt=None):
        """ Read data from a device.

        Args:
            amount (int): How much data to receive at most.
            fmt (str): May be specified instead of amount. Use :mod:`struct`
                        and fmt to return list of values. If only one values is
                        read it is returned directly.
        Returns:
            object: Bytes, object or list of objects read.
        """

        if amount is None:
            amount = struct.calcsize(fmt)

        buf = self.fd.read(amount)

        if fmt:
            buf = struct.unpack(fmt, buf)
            if len(buf) == 1:
                buf = buf[0]

        return buf

    def read_register(self, register, amount=None, fmt=None):
        """ Read data from an register of a device.

        Args:
            register (byte): Address of the register.
            amount (int): How much data to receive at most.
            fmt (str): Optional data format passed to :func:`struct.unpack`
                       with the received buffer.
        Returns:
            object: The received bytes or the unpacked datatype
                    if fmt was given.
        """

        if amount is None:
            amount = struct.calcsize(fmt)

        buf = create_string_buffer(bytes([register]), 1)
        write = Message(addr=self.address, flags=0, len=len(buf), buf=buf)
        buf = create_string_buffer(amount)
        read = Message(addr=self.address, flags=I2C_M_RD, len=len(buf), buf=buf)

        transaction = (Message*2)(write, read)
        message = IoctlData(msgs=transaction, nmsgs=2)
        fcntl.ioctl(self.fd, I2C_RDWR, message)

        data = bytes(buf)
        if amount is not None:
            assert amount == len(data)
        if fmt:
            data = struct.unpack(fmt, data)
            return data[0] if len(data) == 1 else data
        return data

    def __enter__(self):
        # Open the bus file.

        self.fd = io.open(self.path, "r+b", buffering=0)
        flags = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        fcntl.ioctl(self.fd, I2C_SLAVE, self.address)
        return self

    def __exit__(self, *exc_details):
        # Close the bus file.
        self.fd.close()


class I2CMixin:  # pragma: no cover
    """ Provide an reference to an I2C device. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.i2c = None
        self.option("i2c_path", "str", "Path of the I2C bus")
        self.option("i2c_address", "struct/B", "Address of the chip")

        self.add_context(self.__i2c_context)

    @contextmanager
    def __i2c_context(self):
        # Get Handle for the given device.

        with Device(self.i2c_path, self.i2c_address) as i2c:
            self.i2c = i2c
            yield
            self.i2c = None
