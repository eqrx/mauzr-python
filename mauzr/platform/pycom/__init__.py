""" Provide core for pycom devices. """
__author__ = "Alexander Sowitzki"

import logging
import sys
import gc # pylint: disable=import-error
import machine # pylint: disable=import-error
import keys # pylint: disable=import-error
import utime # pylint: disable=import-error

class Core:
    """ Manage program components on pycom platforms."""

    def __init__(self):
        # Sleep to allow user interrupts
        utime.sleep_ms(1000)

        import mauzr.platform.pycom.scheduler
        import mauzr.platform.pycom.led

        self._contexts = []
        self._log = logging.getLogger("<Core>")
        self.scheduler = mauzr.platform.pycom.scheduler.Scheduler()
        self.led = mauzr.platform.pycom.led.LED(self)
        self.gpio = None
        self.spi = None
        self.i2c = None
        self.wlan = None
        self.mqtt = None
        self.sigfox = None
        self.config = keys.config
        self.clean()

    @staticmethod
    def logger(name):
        """ Create a logger instance.

        :param name: Name of the caller that wants to receive the logger.
        :type name: object
        :returns: Logger
        :rtype: object
        """

        return logging.getLogger(name)

    def clean(self):
        """ Free memory. """

        # Force the garbage collector
        gc.collect()
        # pylint: disable=no-member
        self._log.info("GC - Free: %s, Allocated: %s",
                       gc.mem_free(), gc.mem_alloc())

    def __enter__(self):
        # Start the program.

        # No ExitStack, just walk the modules
        [context.__enter__() for context in self._contexts]
        return self

    def __exit__(self, *exc_details):
        # Stop the program.

        # Still no ExitStack
        [context.__exit__(*exc_details) for context in self._contexts]

    def add_context(self, context):
        """ Add a context to be managed by this core.

        :param context: Unit to be added
        :type context: object
        """

        self._contexts.append(context)

    def _setup_sigfox(self):
        """ Setup Sigfox on the SiPy. """

        import mauzr.platform.pycom.sigfox
        self.sigfox = mauzr.platform.pycom.sigfox.Manager()
        self.clean()

    def _setup_wlan(self):
        """ Setup WLAN. """

        import mauzr.platform.pycom.wlan
        self.wlan = mauzr.platform.pycom.wlan.Manager(self)
        self.clean()

    def _setup_mqtt(self, **kwargs):
        """ Setup the MQTT manager and client.

        See :class:`mauzr.mqtt.Manager` and :class:`mauzr.mqtt.pycom.mqtt`.
        Keyword arguments given to this function are passed to both
        constructors.

        :param kwargs: Arguments to pass to manager and client.
        :type kwargs: dict
        """

        from mauzr.platform.mqtt import Manager
        from mauzr.platform.pycom.mqtt import Client
        import mauzr.platform.serializer

        self.mqtt = Manager(self, **kwargs)

        mauzr.platform.serializer.Bool.fmt = "!B"

        self.clean()
        mqtt = Client(self, **kwargs)
        self.clean()
        mqtt.manager = self.mqtt
        self.mqtt.mqtt = mqtt
        self._contexts.append(self.mqtt)

    def _setup_gpio(self):
        """ Setup GPIO. """

        import mauzr.platform.pycom.gpio
        self.gpio = mauzr.platform.pycom.gpio.GPIO()
        self.clean()

    def _setup_spi(self):
        """ Setup SPI. """

        import mauzr.platform.pycom.spi
        self.spi = mauzr.platform.pycom.spi.Bus()
        self.clean()

    def _setup_i2c(self, *args, **kwargs):
        """ Setup I2C. See :class:`mauzr.platform.pycom.i2c.Bus`. """

        import mauzr.platform.pycom.i2c
        self.i2c = mauzr.platform.pycom.i2c.Bus(*args, **kwargs)
        self.add_context(self.i2c)
        self.clean()

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
            self.led.simple_set(self.led.MANUAL)
        except Exception as err:
            sys.print_exception(err) # pylint: disable=no-member
            self.led.simple_set(self.led.FAIL)
            if reset_on_exception:
                machine.reset()
            raise
