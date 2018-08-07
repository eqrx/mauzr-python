""" Mixins for agent functions. """

from contextlib import contextmanager

__author__ = "Alexander Sowitzki"


class PollMixin:
    """ Provide polling a callable regularly. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Task for polling.
        self.poll_task = None

        # Make poll interval configurable.
        self.option("interval", "struct/!I", "Poll intervall in milliseconds")
        self.add_context(self.__poll_context)

    @contextmanager
    def __poll_context(self):
        self.poll_task = self.every(self.interval/1000,
                                    self.poll).enable(instant=True)
        yield
        self.poll_task = None

    def poll(self):
        """ Perfom the poll operation. """

        raise NotImplementedError()
