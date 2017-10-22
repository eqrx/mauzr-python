""" Provide core for upy devices. """
__author__ = "Alexander Sowitzki"

import logging
import sys
import gc # pylint: disable=import-error
import machine # pylint: disable=import-error
import utime # pylint: disable=import-error

class Core:
    """ Manage program components on upy platforms."""

    def __init__(self):
        # Sleep to allow user interrupts
        utime.sleep_ms(1000)

        import mauzr.platform.upy.scheduler
        import mauzr.platform.upy.led

        self._contexts = []
        self._log = logging.getLogger("<Core>")
        self.scheduler = mauzr.platform.upy.scheduler.Scheduler()
        # pylint: disable=eval-used
        self.config = eval(open("config.py").read())
        self.pycom = self.config["pycom"]
        self.led = mauzr.platform.upy.led.LED(self)
        self.gpio = None
        self.spi = None
        self.i2c = None
        self.wlan = None
        self.mqtt = None
        self.sigfox = None
        self._mqtt_client = None
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

        from mauzr.platform.upy.sigfox import Manager
        self.sigfox = Manager()
        self.clean()

    def _setup_wlan(self):
        """ Setup WLAN. """
        from  mauzr.platform.upy.wlan import Manager
        self.wlan = Manager(self)
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
        from mauzr.platform.upy.mqtt import Client
        import mauzr.platform.serializer

        self.mqtt = Manager(self, **kwargs)

        mauzr.platform.serializer.Bool.fmt = "!B"

        self.clean()
        self._mqtt_client = Client(self, **kwargs)
        self.clean()
        self._mqtt_client.manager = self.mqtt
        self.mqtt.mqtt = self._mqtt_client

    def _setup_gpio(self):
        """ Setup GPIO. """

        from mauzr.platform.upy.gpio import GPIO
        self.gpio = GPIO(self)
        self.clean()

    def _setup_spi(self):
        """ Setup SPI. """

        import mauzr.platform.upy.spi
        self.spi = mauzr.platform.upy.spi.Bus()
        self.clean()

    def _setup_i2c(self, *args, **kwargs):
        """ Setup I2C. See :class:`mauzr.platform.upy.i2c.Bus`. """

        from mauzr.platform.upy.i2c import Bus
        self.i2c = Bus(self, *args, **kwargs)
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
                if self.pycom:
                    self.scheduler.handle(block=True)
                else:
                    self._mqtt_client.manage(call_scheduler=True)
                self.clean()
        except KeyboardInterrupt:
            self.led.simple_set(self.led.MANUAL)
        except Exception as err:
            sys.print_exception(err) # pylint: disable=no-member
            self.led.simple_set(self.led.FAIL)
            if reset_on_exception:
                machine.reset()
            raise
