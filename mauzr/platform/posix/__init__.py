""" Bootstrap the mauzr agent on posix systems. """
__author__ = "Alexander Sowitzki"

import contextlib
import threading
import logging
import _thread

class Core:
    """ Manage program components on posix platforms.

    The core can either be started directly by calling :func:`run` or
    by using it as a context manager. The first case blocks, the second case
    spawns a thread that is running the scheduler.

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
        self._contexts = []
        self.scheduler_thread = None
        self._stack = contextlib.ExitStack()
        self.shutdown_event = threading.Event()
        self.scheduler = None
        self.mqtt = None

        self._setup_config(suit, agent, instance, parser)
        self._setup_logging()
        self._setup_scheduler()

    @staticmethod
    def on_failure():
        """ Call when an unrecoverable failure happens.

        Shuts the program down.
        """

        _thread.interrupt_main()

    def _setup_config(self, suit, agent, instance, parser):
        from mauzr.platform.posix.config import Config
        self.config = Config(suit, agent, instance, parser)
        self.config.parse()

    def _setup_logging(self):
        """ Setup logging. """

        level = logging.getLevelName(self.config["log_level"].upper())
        logging.basicConfig(level=level,
                            format="{levelname} {asctime} {name}: {message}",
                            style="{")

    @staticmethod
    def logger(name):
        """ Create a logger instance.

        :param name: Name of the caller that wants to receive the logger.
        :type name: str
        :returns: Logger instance.
        :rtype: logging.Logger
        """

        return logging.getLogger(name)

    def add_context(self, context):
        """ Add a context to be managed by this core.

        :param context: Unit to be added
        :type context: object
        """

        self._contexts.append(context)

    def shutdown(self):
        """Ask the agent to shut down. """

        self.shutdown_event.set()

    def run(self):
        """ Setup modules and units and run the scheduler.

        Block until shutdown is requested.
        """

        self.scheduler_thread = False
        with self:
            with contextlib.suppress(KeyboardInterrupt):
                self.scheduler.run()

    def _run_scheduler(self):
        # Dispatch run.

        try:
            self.scheduler.run()
        except Exception:
            # Interrupt main thread
            self.on_failure()
            raise

    def __enter__(self):
        # Start thread for scheduler if not called by run,
        # start modules and units.

        try:
            for subject in self._contexts:
                if hasattr(subject, "__enter__"):
                    self._stack.enter_context(subject)
            if self.scheduler_thread is not False:
                thread = threading.Thread(target=self._run_scheduler,
                                          name="scheduler")
                self.scheduler_thread = thread
                self.scheduler_thread.start()
            return self
        except Exception:
            self._stack.close()
            raise

    def __exit__(self, *exc_details):
        # Stop scheduler thread if existing, stop modules and units.

        self.shutdown_event.set()
        if self.scheduler_thread is not False:
            self.scheduler_thread.join()

        return self._stack.close()

    def setup_mqtt(self, cfgbase="mqtt", **kwargs):
        """ Setup the MQTT manager and client.

        See :class:`mauzr.platform.mqtt.Manager` and
        :class:`mauzr.platform.posix.mqtt.Client`.
        Keyword arguments given to this function are passed to both
        constructors.

        :param cfgbase: Configuration entry for this unit.
        :type cfgbase: str
        :param kwargs: Keyword arguments that will be merged into the config.
        :type kwargs: dict
        """

        from mauzr.platform.posix.mqtt import Client
        from mauzr.platform.mqtt import Manager
        self.mqtt = Manager(self, cfgbase, **kwargs)
        mqtt = Client(self, cfgbase, **kwargs)
        mqtt.manager = self.mqtt
        self.mqtt.mqtt = mqtt
        self._contexts.append(self.mqtt)

    def _setup_scheduler(self):
        # Setup scheduler.

        from mauzr.platform.posix.scheduler import Scheduler
        self.scheduler = Scheduler(self.shutdown_event)
        self._contexts.append(self.scheduler)
