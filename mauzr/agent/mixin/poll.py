""" Mixins for agent functions. """

from contextlib import contextmanager

__author__ = "Alexander Sowitzki"


class PollMixin:
    """ Provide polling a callable regularly. """

    def __init__(self):
        # Task for polling.
        self.poll_task = self.every(None, self.poll)

        # Make poll interval configurable.
        self.option("interval", "struct/!I", "Poll intervall in milliseconds",
                    cb=self.poll_task.set)
        self.add_context(self.__poll_context)
        print(self.poll_task.set)

    @contextmanager
    def __poll_context(self):
        self.poll_task.enable(instant=True)
        yield
        self.poll_task.disable()


    def poll(self):
        """ Perfom the poll operation. """

        raise NotImplementedError()
