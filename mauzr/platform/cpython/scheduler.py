""" Posix scheduler. """
__author__ = "Alexander Sowitzki"

import time
import threading
import mauzr.platform.scheduler

class Task(mauzr.platform.scheduler.Task):
    """ Posix implementation of task.

    :param scheduler: The scheduler to provide information to.
    :type scheduler: mauzr.platform.scheduler.Scheduler
    :param target: Function to execute
    :type target: function
    :param after: Time in ms to delay the execution of the target after
                  task has been enabled.
    :type after: int
    :param single: If True the task is only executed once. If False the task is
                   executed with the specified delay between executions.
    :type single: bool
    """

    @staticmethod
    def _now():
        # The current time in ms.

        return int(time.time()*1000)

class Scheduler(mauzr.platform.scheduler.Scheduler):
    """ Scheduler for the posix platform.

    :param shutdown_event: Event that signals a shutdown request.
    :type shutdown_event: threading.Event

    .. automethod:: __call__
    """

    def __init__(self, shutdown_event):
        mauzr.platform.scheduler.Scheduler.__init__(self)
        self._shutdown_event = shutdown_event
        # Create event for enabled tasks
        self._enabled_event = threading.Event()
        # Just set the event when task is enabled
        self.on_enabled = self._enabled_event.set

    def __call__(self, target, after, single):
        """ Create a new task.

        :param target: Function to execute
        :type target: function
        :param after: Time in ms to delay the execution of the target after
                      task has been enabled.
        :type after: int
        :param single: If True the task is only executed once. If False the
                       task is executed with the specified delay
                       between executions.
        :type single: bool
        :returns: The newly created task.
        :rtype: mauzr.posix.scheduler.Task
        """

        task = Task(self, target, after, single)
        self.tasks.append(task)
        return task

    def idle(self, delay):
        # Wait the specified amount of time in milliseconds.

        time.sleep(delay/1000)

    def _wait(self):
        # No active tasks are present. Wait and check for new tasks.

        # Wait for the enable event while shutdown is not requested
        while True not in (self._shutdown_event.is_set(),
                           self._enabled_event.is_set()):
            self._enabled_event.wait(timeout=0.1)

    def run(self):
        """ Run the scheduler and process tasks. """

        try:
            # While running
            while not self._shutdown_event.is_set():
                # Clear enabled event
                self._enabled_event.clear()
                # Handle the scheduler
                self._handle()
        finally:
            pass
