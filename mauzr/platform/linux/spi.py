""" SPI for linux systems. """

__author__ = "Alexander Sowitzki"

import spidev # pylint: disable=import-error

class Bus:
    """ Access SPI on upy. """

    def __init__(self, core, cfgbase="spi", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._spi = spidev.SpiDev()
        self._spi.open(*cfg["path"])
        self._baud = cfg["baudrate"]

    def write(self, data):
        """ Write data on the bus.

        :param data: Data to write.
        :type data: bytes
        """

        self._spi.xfer(data, self._baud)
