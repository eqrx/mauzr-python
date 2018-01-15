""" Provide I2C functionality for linux. """

import fcntl
import io
import os
import struct
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
    """

    READ_ACTION = 0
    """ Indicate a read action in a transaction. """
    WRITE_ACTION = 1
    """ Indicate a write action in a transaction. """

    def __init__(self, core, path, address):
        self.path = path
        self.address = address
        self.fd = None
        core.add_context(self)

    def write(self, data):
        """ Write data to a device.

        :param data: Data to write.
        :type data: bytes
        """

        if isinstance(data, (tuple, list)):
            data = bytes(data)
        self.fd.write(data)

    def read(self, amount=None, fmt=None):
        """ Read data from a device.

        :param amount: How much data to receive at most.
        :type amount: int
        :param fmt: May be specified instead of amount. Use :mod:`struct`
                    and fmt to return list of values. If only one values is
                    read it is returned directly.
        :type fmt: str
        :returns: Bytes, object or list of objects read.
        :rtype: object
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

        :param register: Address of the register.
        :type register: byte
        :param amount: How much data to receive at most.
        :type amount: int
        :param fmt: Optional data format passed to :func:`struct.unpack`
            with the received buffer.
        :type fmt: str
        :returns: The received bytes or the unpacked datatype if fmt was given.
        :rtype: object
        """

        if amount is None:
            amount = struct.calcsize(fmt)

        buf = self._transaction(((self.WRITE_ACTION, (register,)),
                                 (self.READ_ACTION, amount)))[0]

        if fmt:
            buf = struct.unpack(fmt, buf)
            return buf[0] if len(buf) == 1 else buf

        return buf

    def _encode_transaction(self, actions):
        for action, data in actions:
            if action == self.READ_ACTION:
                amount = data
                yield _types.Message(addr=self.address,
                                     flags=_types.I2C_M_RD,
                                     len=amount,
                                     buf=create_string_buffer(amount))
            elif action == self.WRITE_ACTION:
                if not isinstance(data, bytes):
                    data = bytes(data)
                yield _types.Message(addr=self.address, flags=0,
                                     len=len(data),
                                     buf=create_string_buffer(data))
            else:
                raise ValueError("Invalid action: {}".format(action))

    def _transaction(self, actions):
        """ Perform an I2C transaction.

        :param actions: Tuple of actions to perform.
        :type actions: tuple
        :returns: Transaction results
        :rtype: tuple
        :raise ValueError: If action is invalid.
        """

        actions = self._encode_transaction(actions)

        # Perform action set with magic
        msgs = (_types.Message * len(actions))(*actions)
        strct = _types.IoctlData(msgs=msgs, nmsgs=len(actions))
        fcntl.ioctl(self.fd, _types.I2C_RDWR, strct)

        # Return all reads
        return [msg.buf for msg in actions if msg.flags == _types.I2C_M_RD]

    def __enter__(self):
        # Open the bus file.

        self.fd = io.open(self.path, "r+b", buffering=0)
        flags = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        fcntl.ioctl(self.fd, _types.I2C_SLAVE, self.address)
        return self

    def __exit__(self, *exc_details):
        # Close the bus file.
        self.fd.close()


class Bus:
    """ Manage an I2C bus.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Configuration:**

        - **baudrate** (:class:`int`) - Baudrate of the bus.
        - **pins** (:class:`tuple`) - Pins to use for the bus (SDA, SCL) \
            as tuple of strings.
    """

    def __init__(self, core, cfgbase="i2c", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._core = core
        self._path = cfg["path"]

    def __call__(self, address):
        """ Create a device handle.

        :param address: Address of the device.
        :type address: int
        :returns: The device handle.
        :rtype: Device
        """

        return Device(self._core, self._path, address)
