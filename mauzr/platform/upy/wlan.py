""" WLAN for upy systems. """

import mauzr.platform.pycom.wlan
import network # pylint: disable=import-error

class Manager(mauzr.platform.pycom.wlan.Manager):
    """ Manage WLAN connections. """

    @staticmethod
    def _setup():
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        return wlan

    def _connect(self, ssid, password, _timeout):
        self._wlan.connect(ssid, password)
