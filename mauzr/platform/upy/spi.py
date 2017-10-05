""" SPI for upy systems. """
__author__ = "Alexander Sowitzki"

import machine # pylint: disable=import-error

class Bus:
    """ Access SPI on upy.

    :param baudrate: Baudrate to use for the bus.
    :type baudrate: int
    """

    def __init__(self, baudrate=1000000):
        # Use bus 0
        self._spi = machine.SPI(0)
        # Init bus
        self._spi.init(machine.SPI.MASTER, baudrate=baudrate)

    def write(self, data):
        """ Write data on the bus.

        :param data: Data to write.
        :type data: bytes
        """

        self._spi.write(data)

    def read(self, amount):
        """ Read data from the bus.

        :param amount: Number of bytes to read.
        :type amount: int
        :returns: Bytes read
        :rtype: bytes
        """

        return self._spi.read(amount)
