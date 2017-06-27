""" Sigfox access for pycom. """
__author__ = "Alexander Sowitzki"

import logging
import usocket # pylint: disable=import-error
import network # pylint: disable=import-error

class Manager:
    """ Manage the Sigfox module on pycom platforms. """

    def __init__(self):
        self._log = logging.getLogger("<Sigfox>")

        # Set to region europe
        network.Sigfox(mode=network.Sigfox.SIGFOX, rcz=network.Sigfox.RCZ1)
        # Create Socket
        self._sigfox = usocket.socket(usocket.AF_SIGFOX, usocket.SOCK_RAW)
        # We do not care about RX
        self._sigfox.setsockopt(usocket.SOL_SIGFOX, usocket.SO_RX, False)

    def send(self, data):
        """ Send data via sigfox.

        :param data: Data to send.
        :type data: bytes
        """

        self._log.info("Sending %s", data)
        self._sigfox.send(data)
