""" Base for drivers. """

from mauzr.serializer import Struct

__author__ = "Alexander Sowitzki"


def guard(exceptions, suppress=False, ignore_ready=False):
    """ Create decorator to handle raised exceptions for drivers.

    :param exceptions: List of exceptions to catch.
    :type exceptions: tuple
    :param suppress: Don't reraise exception if True.
    :type suppress: bool
    :param ignore_ready: Ignore ready state of driver.
    :type ignore_ready: bool
    :returns: Created decorator
    :rtype: callable
    """

    def guard_decorator(func):
        """ Decorator to handle raised exceptions for drivers.

        :param func: Function to guard.
        :type func: callable
        :returns: Function wrapper.
        :rtype: callable
        """

        def wrapper(*args, **kwargs):
            """ Wrap function and handle raised exceptions for drivers. """

            # Extract self
            # pylint: disable=protected-access
            self = args[0]
            # Ensure driver is ready
            if not self._ready and not ignore_ready:
                if not suppress:
                    raise DriverError("Driver not ready")
                return

            try:
                return func(*args, **kwargs)
            except exceptions as err:
                self._log.error(str(err))
                self._on_error(err)
                if not suppress:
                    raise DriverError(err)

        return wrapper
    return guard_decorator


class DriverError(Exception):
    """ Exception representing an recoverable driver error. """

    pass


class Driver:
    """ Base for drivers.

    :param core: Core instance.
    :type core: object
    :param name: Log name of this.
    :type name: str
    :param init_delay: Delay between inits in milliseconds.
    :type init_delay: int

    .. automethod:: _init
    .. automethod:: _reset
    """

    def __init__(self, core, name, init_delay=3000):
        self._init_task = core.scheduler(self._init, init_delay, single=True)
        self._ready = False
        core.add_context(self)
        self._log = core.logger(name)
        self._mqtt = core.mqtt

    def __enter__(self):
        """ Perform init. """

        self._init()
        return self

    def __exit__(self, *exc_details):
        """ Perform reset. """
        self._reset()

    def _set_ready(self, value):
        """ Set ready value.

        If True the driver is ready to operate.
        If False driver operations will fail.
        """

        self._ready = value

    def _init(self):
        """ Setup hardware. """

        self._set_ready(True)
        self._log.info("Init done")

    def _on_error(self, err):
        """ Called if an error happens within the driver.

        :param err: The causing error.
        :type err: Exception
        """

        # Not ready anymore.
        self._set_ready(False)
        # Schedule reinit.
        self._init_task.enable()

    def _reset(self):
        """ Reset hardware. """

        # Not ready anymore.
        self._set_ready(False)
        self._log.info("Reset done")


class PollingDriver(Driver):
    """ Base for drivers that poll values regularly.

    :param core: Core instance.
    :type core: object
    :param name: Driver name.
    :type name: str
    :param base: Base topic of the driver.
    :type base: str
    :param poll_interval: Delay between polls in milliseconds
    :type poll_interval: int
    :param init_delay: Delay between inits in milliseconds.
    :type init_delay: int

    .. automethod:: _init
    .. automethod:: _reset
    .. automethod:: _poll
    """

    NAME_FMT = "<{}@{}>"
    """ String format for the log name. """

    def __init__(self, core, base, name, poll_interval, init_delay=3000):
        Driver.__init__(self, core,
                        self.NAME_FMT.format(name, base), init_delay)
        self.poll_task = core.scheduler(self._dispatch_poll, poll_interval,
                                        False)
        self._poll_interval = poll_interval
        self._mqtt.subscribe(base + "poll_interval", self._on_interval,
                             Struct("!I"), 0)

    def _on_interval(self, _topic, interval):
        self._poll_interval = interval
        if self._ready:
            self.poll_task.enable(after=interval, instant=True)

    def _dispatch_poll(self):
        self._poll()

    def _poll(self):
        raise NotImplementedError()

    def _set_ready(self, value):
        super()._set_ready(value)
        if value:
            self.poll_task.enable(after=self._poll_interval, instant=True)
        else:
            self.poll_task.disable()


class DelayedPollingDriver(PollingDriver):
    """ Base for divers that poll values regularly and need a delay
    between value poll and fetch.

    :param core: Core instance.
    :type core: object
    :param base: Topic base of the driver.
    :type base: str
    :param name: Log name of this.
    :type name: str
    :param poll_interval: Delay between polls in milliseconds
    :type poll_interval: int
    :param receive_delay: Delay between poll and receive in milliseconds:
    :type receive_delay: int
    :param init_delay: Delay between inits in milliseconds.
    :type init_delay: int
    """

    def __init__(self, core, base, name, poll_interval,
                 receive_delay, init_delay=3000):
        PollingDriver.__init__(self, core, base, name,
                               poll_interval, init_delay)
        # Delay must be smaller than interval.
        if poll_interval <= receive_delay:
            raise ValueError("Poll interval ({}) must be greater "
                             "than receive delay ({}).".format(poll_interval,
                                                               receive_delay))
        self._receive_task = core.scheduler(self._receive, receive_delay,
                                            True)

    def _receive(self):
        """ Receive value once. """

        raise NotImplementedError()

    def _dispatch_poll(self):
        super()._dispatch_poll()
        self._receive_task.enable()

    def _set_ready(self, value):
        super()._set_ready(value)
        # Enable/Disable task according to ready state.
        if not value:
            self._receive_task.disable()
