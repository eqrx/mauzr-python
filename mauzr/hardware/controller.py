""" Controller basics. """

__author__ = "Alexander Sowitzki"


class Publisher:
    """ Base for controllers.

    :param core: Core instance.
    :type core: object
    :param name: Log name of this.
    :type name: str

    .. automethod:: _init
    .. automethod:: _reset
    """

    def __init__(self, core, name):
        core.add_context(self)
        self._mqtt = core.mqtt
        self._log = core.logger(name)

    def __enter__(self):
        # Call init.

        self._init()
        return self

    def __exit__(self, *exc_details):
        # Call reset.

        self._reset()

    def _init(self):
        """ Init the publisher.

        By default this just calls :func:`reset`.
        """

        self._reset()

    def _reset(self):
        """ Reset the publisher. """
        pass


class TimedPublisher(Publisher):
    """ Base for controllers with a fixed output rate.

    :param core: Core instance.
    :type core: object
    :param name: Log name of this.
    :type name: str
    :param interval: Delay between publishes in milliseconds.
    :type interval: int

    .. automethod:: _init
    .. automethod:: _reset
    .. automethod:: _publish
    """

    def __init__(self, core, name, interval):
        Publisher.__init__(self, core, name)
        self._publish_task = core.scheduler(self._publish, interval, False)

    def _publish(self):
        """ When called, inheriting classes shall publish the value.

        :raises NotImplementedError: When not implemented.
        """
        raise NotImplementedError()

    def _init(self):
        """ Enable fire task. """

        self._publish_task.enable(instant=True)

    def _reset(self):
        """ Disable fire task. """

        self._publish_task.disable()
