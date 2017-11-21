""" Provide core for raspberry devices. """
__author__ = "Alexander Sowitzki"

import mauzr.platform.linux

class Core(mauzr.platform.linux.Core):
    """ Manage program components on raspberry platforms.

    Arguments will be passed to :class:`mauzr.platform.posix.Core`.
    """

    def __init__(self, *args, **kwargs):
        mauzr.platform.linux.Core.__init__(self, *args, **kwargs)
        self.i2c = None
        self.gpio = None

    def setup_gpio(self, **kwargs):
        """ Setup GPIO.

        See :class:`mauzr.platform.raspberry.gpio.Pins`
        """

        from mauzr.platform.raspberry.gpio import Pins
        self.gpio = Pins(self, **kwargs)

    def setup_i2c(self, *args, **kwargs):
        """ Setup I2C.

        See :class:`mauzr.platform.raspberry.i2c.Bus`
        """

        from mauzr.platform.raspberry.i2c import Bus
        self.i2c = Bus(self, *args, **kwargs)
