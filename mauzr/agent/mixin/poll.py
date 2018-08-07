""" Mixins for agent functions. """

from contextlib import contextmanager

__author__ = "Alexander Sowitzki"


class PollMixin:
    """ Provide polling a callable regularly. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Task for polling.
        self.poll_task = self.every(None, self.poll)

        # Make poll interval configurable.
        self.option("interval", "struct/!I", "Poll intervall in milliseconds",
                    cb=lambda x: self.poll_task.set(x/1000))
        self.add_context(self.__poll_context)

    @contextmanager
    def __poll_context(self):
        self.poll_task.enable(instant=True)
        yield
        self.poll_task.disable()


    def poll(self):
        """ Perfom the poll operation. """

        raise NotImplementedError()
