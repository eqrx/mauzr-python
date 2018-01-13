""" Provide core for docker agents. """

import mauzr.platform.linux

__author__ = "Alexander Sowitzki"


class Core(mauzr.platform.linux.Core):
    """ Manage program components on docker agents.

    Arguments will be passed to :class:`mauzr.platform.linux.Core`.
    """

    def __init__(self, *args, **kwargs):
        mauzr.platform.linux.Core.__init__(self, *args, **kwargs)

    def setup_gpio(self, **kwargs):
        """ Setup GPIO.

        See :class:`mauzr.platform.docker.gpio.Pins`
        """

        from mauzr.platform.docker.gpio import Pins
        self.gpio = Pins(self, **kwargs)
