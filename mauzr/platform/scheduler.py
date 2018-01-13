""" Common parts for a task scheduler. """

import logging

__author__ = "Alexander Sowitzki"


class Task:
    """ Represents a single or recurring task that can be executed.

    Note that the task has to be enabled before it can run.

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

    def __init__(self, scheduler, target, after, single):
        self._single = single
        self._scheduler = scheduler
        self._target = target
        self._after = after
        self.execution = None

    @staticmethod
    def _now():
        raise NotImplementedError()

    def enable(self, instant=False, after=None):
        """ Enable the task.

        :param instant: If true the first time the task will be executed
                        without delay. Use this for startup.
        :type instant: bool
        :param after: New afer value to set.
        :type after: int
        :return: Self for convenience.
        :rtype: mauzr.platform.scheduler.Task
        """

        if after is not None:
            self._after = after

        self.execution = 0 if instant else self._now() + self._after
        # Inform scheduler
        self._scheduler.on_enabled()

        return self

    def disable(self):
        """ Disable / cancel this task. No effect if already running. """

        self.execution = None
        return self

    @property
    def enabled(self):
        """
        :returns: True if the task in enabled.
        :rtype: bool
        """

        return self.execution is not None

    @property
    def pending_in(self):
        """
        :returns: Time in milliseconds until the next execution.
        :rtype: int
        """

        return self.execution - self._now()

    @property
    def pending(self):
        """
        :returns: True if the task if currently pending for execution.
        :rtype: bool
        """

        return self.pending_in <= 0

    def _next_execution(self):
        """
        :returns: The time of the next execution in milliseconds
        :rtype: int
        """

        # Single task, no next time
        return None if self._single else self._now() + self._after

    def execute(self):
        """ Execute the task. """

        # Do not execute if task was canceled
        if self.execution is None:
            return
        # Schedule next execution
        self.execution = self._next_execution()
        # Run task
        self._target()


class Scheduler:
    """ Schedules tasks that are executed by a single runner. """

    def __init__(self):
        self.tasks = []
        self._log = logging.getLogger(self.__class__.__name__)

    def on_enabled(self):
        """ Called when a task was enabled. """

        pass

    def on_delayed(self, task):
        """ Called when a task was called to late.

        :param task: A task that was executed with a delay.
        :type task: mauzr.platform.scheduler.Task
        """

        # Print a complaint
        self._log.warning("Task delayed.")

    @staticmethod
    def idle(delay):
        """ Wait the specified delay.

        :raise NotImplementedError: If not overwritten.
        """

        raise NotImplementedError()

    @staticmethod
    def _wait():
        """ Wait until tasks have been enabled.

        :raise NotImplementedError: If not overwritten.
        """

        raise NotImplementedError()

    def _handle(self):
        """ Handle the current state of the scheduler. """

        # Fetch all active tasks
        active_tasks = [task for task in self.tasks if task.enabled]
        # Fetch all pending tasks
        pending_tasks = [task for task in active_tasks if task.pending]

        if pending_tasks:
            # There are pending tasks, execute them all and bail
            for task in pending_tasks:
                task.execute()
        elif active_tasks:
            # No pending tasks but active tasks, wait for the next one
            d = min([task.pending_in for task in active_tasks] + [300])
            self.idle(d)
        else:
            # No active tasks, go idle
            self._wait()
