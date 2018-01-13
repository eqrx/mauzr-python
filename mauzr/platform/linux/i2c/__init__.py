""" Provide I2C functionality for linux. """

import fcntl
import io
import os
import threading
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

    READ = 0
    """ Indicate a read action in a transaction. """
    WRITE = 1
    """ Indicate a write action in a transaction. """

    def __init__(self, core, path, address):
        self.device = path
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

        if amount is None and fmt is not None:
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

        if amount is None and fmt is not None:
            amount = struct.calcsize(fmt)

        buf = self.transaction(((self.WRITE, (register,)),
                                (self.READ, amount)))[0]

        if fmt:
            buf = struct.unpack(fmt, buf)
            if len(buf) == 1:
                buf = buf[0]

        return buf

    def transaction(self, actions):
        """ Perform an I2C transaction.

        :param actions: Tuple of actions to perform.
        :type actions: tuple
        :returns: Transaction results
        :rtype: tuple
        :raise ValueError: If action is invalid.
        """

        read_actions = []
        coded_actions = []

        # Encode all actions in list
        for action, data in actions:
            if action == self.READ:
                amount = data
                read = _types.Message(addr=self.address,
                                      flags=_types.I2C_M_RD,
                                      len=amount,
                                      buf=create_string_buffer(amount))
                read_actions.append(read)
                coded_actions.append(read)
            elif action == self.WRITE:
                if not isinstance(data, bytes):
                    data = bytes(data)
                write = _types.Message(addr=self.address, flags=0,
                                       len=len(data),
                                       buf=create_string_buffer(data))
                coded_actions.append(write)
            else:
                raise ValueError("Invalid action: {}".format(action))
        action_count = len(coded_actions)
        if action_count == 0:
            raise ValueError("Plz don't break the system")

        # Perform action set with magic
        msgs = (_types.Message * action_count)(*coded_actions)
        strct = _types.IoctlData(msgs=msgs, nmsgs=action_count)
        fcntl.ioctl(self.fd, _types.I2C_RDWR, strct)

        # Return all reads
        return [read.buf for read in read_actions]

    def __enter__(self):
        # Open the bus file.

        self.fd = io.open(self.device, "r+b", buffering=0)
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
    :param path: Path to the device file.
    :type path: str
    """

    READ = 0
    """ Indicate a read action in a transaction. """
    WRITE = 1
    """ Indicate a write action in a transaction. """

    def __init__(self, core, path):
        self.current_address = None
        self.device = path
        self.lock = threading.RLock()
        self.fd = None
        core.add_context(self)

    @staticmethod
    def base_address(address):
        """
        :param address: The address to extract from.
        :type address: byte
        :returns: Device address from a combined address.
        :rtype: int
        """

        return address

    def _select_device(self, address):
        # Set the bus to communicate to a device.

        if self.current_address != address:
            fcntl.ioctl(self.fd, _types.I2C_SLAVE, address)
            self.current_address = address

    def write(self, address, data):
        """ Write data to a device.

        :param address: The address of the device.
        :type address: object
        :param data: Data to write.
        :type data: bytes
        """

        if isinstance(data, (tuple, list)):
            data = bytes(data)

        with self.lock:
            self._select_device(address)
            self.fd.write(data)

    def read(self, address, amount=None, fmt=None):
        """ Read data from a device.

        :param address: The address of the device.
        :type address: object
        :param amount: How much data to receive at most.
        :type amount: int
        :param fmt: May be specified instead of amount. Use :mod:`struct`
                    and fmt to return list of values. If only one values is
                    read it is returned directly.
        :type fmt: str
        :returns: Bytes, object or list of objects read.
        :rtype: object
        """

        if amount is None and fmt is not None:
            amount = struct.calcsize(fmt)

        with self.lock:
            self._select_device(address)
            buf = self.fd.read(amount)

        if fmt:
            buf = struct.unpack(fmt, buf)
            if len(buf) == 1:
                buf = buf[0]

        return buf

    def read_register(self, address, register, amount=None, fmt=None):
        """ Read data from an register of a device.

        :param address: The address of the device.
        :type address: object
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

        if amount is None and fmt is not None:
            amount = struct.calcsize(fmt)

        buf = self.transaction(address, ((self.WRITE, bytes([register])),
                                         (self.READ, amount)))[0]

        if fmt:
            buf = struct.unpack(fmt, buf)
            if len(buf) == 1:
                buf = buf[0]

        return buf

    def transaction(self, address, actions):
        """ Perform an I2C transaction.

        :param address: Address of the device to communicate with.
        :type address: object
        :param actions: Tuple of actions to perform.
        :type actions: tuple
        :returns: Transaction results
        :rtype: tuple
        :raise ValueError: If action is invalid.
        """

        with self.lock:
            # Select device and manage addresses
            self._select_device(address)
            read_actions = []
            coded_actions = []

            base_address = self.base_address(address)

            # Encode all actions in list
            for action, data in actions:
                if action == self.READ:
                    read = _types.Message(addr=base_address,
                                          flags=_types.I2C_M_RD,
                                          len=data,
                                          buf=create_string_buffer(data))
                    read_actions.append(read)
                    coded_actions.append(read)
                elif action == self.WRITE:
                    if not isinstance(data, bytes):
                        data = bytes(data)
                    write = _types.Message(addr=base_address, flags=0,
                                           len=len(data),
                                           buf=create_string_buffer(data))
                    coded_actions.append(write)
                else:
                    raise ValueError("Invalid action: {}".format(action))
            action_count = len(coded_actions)
            if action_count == 0:
                raise ValueError("Plz don't break the system")

            # Perform action set with magic
            msgs = (_types.Message * action_count)(*coded_actions)
            strct = _types.IoctlData(msgs=msgs, nmsgs=action_count)
            fcntl.ioctl(self.fd, _types.I2C_RDWR, strct)

            # Return all reads
            return [read.buf for read in read_actions]

    def __enter__(self):
        # Open the bus file.

        self.fd = io.open(self.device, "r+b", buffering=0)
        flags = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        return self

    def __exit__(self, *exc_details):
        # Close the bus file.

        self.fd.close()


class MultiplexerBus(Bus):
    """ Manage an I2C with an TCA9548A attached.

    :param path: Path of the bus.
    :type path: str
    :param multiplexer_address: Address of the multiplexer
    :type multiplexer_address: byte
    """

    def __init__(self, path, multiplexer_address):
        Bus.__init__(self, path)
        self.multiplexer_address = multiplexer_address

    @staticmethod
    def base_address(address):
        """
        :param address: The address to extract from.
        :type address: byte
        :returns: Device address from a combined address.
        :rtype: int
        """

        return address[1]

    def _select_device(self, address):
        # Set the bus to communicate to a device.

        if len(address) != 2:
            raise ValueError("Address must have subbus id and device id")
        if self.current_address != address:
            bus_id, device_address = address
            fcntl.ioctl(self.fd, _types.I2C_SLAVE, self.multiplexer_address)
            self.fd.write(bytes([bus_id]))
            fcntl.ioctl(self.fd, _types.I2C_SLAVE, device_address)
            self.current_address = address


class MultiMultiplexerBus(Bus):
    """ Manage an I2C with multiple TCA9548A attached.

    :param path: Path of the bus.
    :type path: str
    """

    def __init__(self, path):
        Bus.__init__(self, path)

    @staticmethod
    def base_address(address):
        """
        :param address: The address to extract from.
        :type address: byte
        :returns: Device address from a combined address.
        :rtype: int
        """

        return address[3]

    def _select_device(self, address):
        # Set the bus to communicate to a device.

        if len(address) != 3:
            raise ValueError("Address must have multiplexer id,"
                             " subbus id and device id")
        if self.current_address != address:
            multiplexer_address, bus_id, device_address = address
            fcntl.ioctl(self.fd, _types.I2C_SLAVE, multiplexer_address)
            self.fd.write(bytes([bus_id]))
            fcntl.ioctl(self.fd, _types.I2C_SLAVE, device_address)
            self.current_address = address
