""" Provide core for upy devices. """
__author__ = "Alexander Sowitzki"

import logging
import sys
import machine # pylint: disable=import-error
import utime # pylint: disable=import-error
import mauzr.platform.pycom
import mauzr.platform.pycom.scheduler

class Core(mauzr.platform.pycom.Core):
    """ Manage program components on upy platforms."""

    def __init__(self):
        # pylint: disable=super-init-not-called
        # Sleep to allow user interrupts
        utime.sleep_ms(1000)

        self._contexts = []
        self._log = logging.getLogger("<Core>")
        self.scheduler = mauzr.platform.pycom.scheduler.Scheduler()
        self.gpio = None
        self.spi = None
        self.i2c = None
        self.wlan = None
        self.mqtt = None
        # pylint: disable=eval-used
        self.config = eval(open("config.py").read())
        self.clean()

    def _setup_wlan(self):
        """ Setup WLAN. """

        from  mauzr.platform.upy.wlan import Manager
        self.wlan = Manager(self)
        self.clean()

    @staticmethod
    def on_failure():
        """ Call when an unrecoverable failure happens. """

    def run(self, reset_on_exception):
        """ Run the program. This blocks until the program is finished.

        :param reset_on_exception: If true the :func:`machine.reset` is called
                                   if an exeption other than
                                   :class:`KeyboardInterrupt` if raised.
        :type reset_on_exception: bool
        :raises Exception: If the program fails for some reason.
        """

        try:
            with self:
                self.clean()
                self.scheduler.run()
                self.clean()
        except KeyboardInterrupt:
            pass
        except Exception as err:
            sys.print_exception(err) # pylint: disable=no-member
            if reset_on_exception:
                machine.reset()
            raise
