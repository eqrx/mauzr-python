""" Provide I2C functionality for pycm devices. """
__author__ = "Alexander Sowitzki"

import ustruct # pylint: disable=import-error
import machine # pylint: disable=import-error

class Bus:
    """ Manage an I2C bus.

    :param baudrate: Baudrate of the bus.
    :type baudrate: int
    :param pins: Pins to use for the bus (SDA, SCL).
    :type pins: tuple
    """

    def __init__(self, baudrate=400000, pins=("P9", "P10")):
        self.baudrate = baudrate
        self.i2c = machine.I2C(0)
        self.pins = pins

    def __enter__(self):
        # Init bus.

        self.i2c.init(machine.I2C.MASTER, baudrate=self.baudrate,
                      pins=self.pins)
        return self

    def __exit__(self, *exec_details):
        # Deinit bus.

        pass

    def write(self, address, data):
        """ Write data to a device.

        :param address: The address of the device.
        :type address: object
        :param data: Data to write.
        :type data: bytes
        :returns: Number of bytes written.
        :rtype: int
        """

        if not isinstance(data, (bytearray, bytes)):
            # Convert data to bytes if this hasn't happened already
            data = bytes(data)

        return self.i2c.writeto(address, data)

    def read(self, address, amount):
        """ Read data from a device.

        :param address: The address of the device.
        :type address: object
        :param amount: How much data to receive at most.
        :type amount: int
        :returns: Bytes read.
        :rtype: bytes
        """

        return self.i2c.readfrom(address, amount)

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
            # Calculate amount if fmt is given and amount is not set
            amount = ustruct.calcsize(fmt)

        value = self.i2c.readfrom_mem(address, register, amount)

        if fmt:
            # Unpack value if fmt set
            value = ustruct.unpack(fmt, value)
            if len(value) == 1:
                # If unpacked list contains only one value pass it
                value = value[0]

        return value
