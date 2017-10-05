""" Provide pycom specific functions. """
__author__ = "Alexander Sowitzki"

try:
    import pycom # pylint: disable=import-error
except ImportError:
    pass

class LED:
    """ Manage the status LED on the board.

    :param core: Core instance to use.
    :type core: object
    """

    FAIL = 0xff0000
    """ Color for system failure. """

    RUN = 0x000200
    """ Color for system operational. """

    BEAT = 0x000002
    """ Color for system heartbeat. """

    DISCONNECTED = 0xff00ff
    """ Color for system disconnection. """

    MANUAL = 0xffffff
    """ Color for system in manual mode. """

    ACT = 0x000202
    """ Color for system acting. """

    INIT = 0xff9000
    """ Color for system init. """

    def __init__(self, core):
        self.pycom = core
        if self.pycom:
            # Disable default heartbeat
            pycom.heartbeat(False)
        # Default state is init
        self._state = self.INIT
        self.simple_set(self._state)

        self._core = core
        self._check_task = core.scheduler(self._check, 3000, single=True)
        self._check_task.enable()
        self._reset_task = core.scheduler(self._reset, 1000, single=True)

    def _reset(self):
        # Reset the LED to the last state.

        self.simple_set(self._state)
        self._check_task.enable()

    def _check(self):
        # Check system functions.

        if self._core.wlan is not None and not self._core.wlan.connected:
            # Mark as disconnected if WLAN is not connected
            self._state = self.DISCONNECTED
        elif self._core.mqtt is not None and not self._core.mqtt.connected:
            # Mark as disconnected if MQTT is not connected
            self._state = self.DISCONNECTED
        else:
            # Else mark as running
            self._state = self.RUN

        # Set beat for one tick
        self.set(self.BEAT)

    def set(self, color):
        """ Set a color for one display frame.

        :param color: Color to set.
        :type color: int
        """

        # Set color
        self.simple_set(color)
        # Schedule reset
        self._reset_task.enable()

    def simple_set(self, color):
        """ Set the color.

        :param color: Color to set.
        :type color: int
        """

        if self.pycom:
            pycom.rgbled(color)
