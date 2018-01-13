""" Bootstrap the mauzr agent on linux systems. """

import mauzr.platform.cpython

__author__ = "Alexander Sowitzki"


class Core(mauzr.platform.cpython.Core):
    """ Manage program components on linux platforms.

    :param suit: Suit this agent belongs to.
    :type suit: str
    :param agent: Name of the agent.
    :type agent: str
    :param instance: Instance of this agent. May be None
    :type instance: str
    :param parser: Argparse instance to use. If None, a new one will be used.
    :type parser: argparse.ArgumentParser
    """

    def __init__(self, suit, agent, instance=None, parser=None):
        mauzr.platform.cpython.Core.__init__(self, suit, agent,
                                             instance, parser)
        self.database = None
        self.i2c = None
        self.gpio = None
        if self.config.get("systemd", False):
            from mauzr.platform.linux.systemd import Systemd
            self.add_context(Systemd(self))

    def setup_gpio(self, **kwargs):
        """ Setup GPIO.

        See :class:`mauzr.platform.linux.gpio.Pins`
        """

        from mauzr.platform.linux.gpio import Pins
        self.gpio = Pins(self, **kwargs)

    def setup_i2c(self, *args, **kwargs):
        """ Setup I2C.

        See :class:`mauzr.platform.linux.i2c.Bus`
        """

        from mauzr.platform.linux.i2c import Bus
        self.i2c = Bus(self, *args, **kwargs)
