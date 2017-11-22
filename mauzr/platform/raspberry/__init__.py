""" Provide core for raspberry devices. """
__author__ = "Alexander Sowitzki"

import mauzr.platform.linux

class Core(mauzr.platform.linux.Core):
    """ Manage program components on raspberry platforms.

    Arguments will be passed to :class:`mauzr.platform.posix.Core`.
    """

    def __init__(self, *args, **kwargs):
        mauzr.platform.linux.Core.__init__(self, *args, **kwargs)
        self.gpio = None

    def setup_gpio(self, **kwargs):
        """ Setup GPIO.

        See :class:`mauzr.platform.raspberry.gpio.Pins`
        """

        from mauzr.platform.raspberry.gpio import Pins
        self.gpio = Pins(self, **kwargs)
