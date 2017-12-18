""" SPI for upy systems. """
__author__ = "Alexander Sowitzki"

import machine # pylint: disable=import-error

class Bus:
    """ Access SPI on upy. """

    def __init__(self, core, configbase="spi", **kwargs):
        cfg = core.config[configbase]
        cfg.update(kwargs)

        # Use bus 0
        self._spi = machine.SPI(0)
        # Init bus
        self._spi.init(machine.SPI.MASTER, baudrate=cfg["baudrate"])

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
