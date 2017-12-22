""" WLAN for upy systems. """
__author__ = "Alexander Sowitzki"

import logging
import network # pylint: disable=import-error

class Manager:
    """ Manage WLAN connections.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Configuration:**

        - **networks** (:class:`dict`: A list of dictionaries containing \
            ssid, password and connection timeout in milliseconds.
    """
    def __init__(self, core, cfgbase="wlan", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)
        self._log = logging.getLogger("<WLAN>")

        self._maintain_task = core.scheduler(self._maintain, 10000,
                                             single=False)
        self._delay_task = core.scheduler(self._delayed, 20000,
                                          single=True)
        self._networks = cfg["networks"]
        self._current_config = 0


        network.WLAN(network.AP_IF).active(False)
        self._wlan = network.WLAN(network.STA_IF)
        self._wlan.active(True)
        self._maintain_task.enable(instant=True)

    def _delayed(self):
        # Called after a maintainance delay was performed.

        self._maintain_task.enable()

    @property
    def connected(self):
        """
        :returns: True if wireless is connected.
        :rtype: bool
        """

        return self._wlan.isconnected()

    def _connect(self, ssid, password, _timeout):
        self._wlan.connect(ssid, password)

    def _maintain(self):
        # Maintain wlan connection.

        if not self._wlan.isconnected():
            cfg = self._networks[self._current_config]
            self._log.info("Attempting connection to %s", cfg["ssid"])
            self._connect(cfg["ssid"], cfg["password"],
                          cfg.get("timeout", 3000))

            if self._current_config == len(self._networks) - 1:
                self._maintain_task.disable()
                self._delay_task.enable()
            else:
                self._current_config += 1
