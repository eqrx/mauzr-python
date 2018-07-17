""" Common parts for a task scheduler. """

import time
import weakref
import threading

__author__ = "Alexander Sowitzki"


class Task:
    """ A task that is to be run by the scheduler.

    Args:
        sched (Scheduler): Scheduler to execute the task.
        delay (float): Delay to the next execution.
        repeat (bool): If True, the task will fire multiple times with \
                       given delay in between.
        cb (callable): Callable to call when timer fires.
        args (tuple): Positional arguments for callable.
        kwargs (dict): Keyword arguments for callable.
    """

    def __init__(self, sched, delay, repeat, cb, args, kwargs):
        self.sched = sched
        self.cb = cb
        self.delay = delay
        self.repeat = repeat
        self.at = None
        self.args = args
        self.kwargs = kwargs
        self.time_func = time.monotonic

    def __lt__(self, other):
        """ Compare which task is due first.

        Args:
            other (Task): Task to compare with.
        Returns:
            bool: True if this task is due first.
        """

        at, other_at = self.at, other.at
        if at is None:
            # If self not scheduled self is placed after
            return False
        elif other_at is None:
            # If other is not scheduler self is placed before
            return True
        return at < other_at

    def fire(self):
        """ Fire the task. """

        if not self:
            raise RuntimeError("Fired task is not active")

        if self.repeat:
            # If task is repeating record next execution
            self.at = self.time_func() + self.delay
        else:
            # Clear execution timestamp
            self.at = None
        # Inform scheduler task changed
        self.sched.tasks_changed = True
        # Fire callback
        self.cb(*self.args, **self.kwargs)

    def enable(self, instant=False):
        """ Task will be executed after given delay if delay not True.

        Args:
            instant (bool): If True, next execution date is changed to now.
        Returns:
            Task: This task.
        """

        self.at = self.time_func()
        if not instant:
            self.at += self.delay
        self.sched.tasks_changed = True
        return self

    def disable(self):
        """ Disable the task and stop further firing.

        Returns:
            Task: This task.
        """

        self.at = None
        self.sched.tasks_changed = True
        return self

    def __bool__(self):
        """
        Returns:
            bool: True if the task is enabled.
        """

        return self.at is not None


class Scheduler:
    """ Scheduler that executes tasks and callbacks

    Args:
        shell (mauzr.shell.Shell): Program shell.
    """

    def __init__(self, shell):
        self.log = shell.log.getChild("sched")
        self.log.debug("Setting up scheduler")
        self.tasks = []
        self.idle_cb = time.sleep
        self.main_cb = None
        self.thread = None
        self.tasks_changed = False
        self.max_sleep = shell.args.max_sleep
        self.shutdown_request = threading.Event()
        self.main_changed = threading.Event()

    @staticmethod
    def delay_to(task):
        """ Compute needed time delay to reach execution point of a task.

        Returns:
            float: Seconds to task expiration.
        """

        return task.at - task.time_func()

    def every(self, delay, cb, *args, **kwargs):
        """ Create task that will be executed regulary with delay in between.

        Must be enabled first.

        Args:
            delay (float): Delay between executions.
            cb (callable): Callable to call when timer fires.
            args (tuple): Positional arguments for callable.
            kwargs (dict): Keyword arguments for callable.
        Returns:
            Task: Created task.
        """

        t = Task(sched=self, delay=delay, cb=cb, repeat=True,
                 args=args, kwargs=kwargs)
        self.tasks.append(weakref.ref(t, self.tasks.remove))
        return t

    def after(self, delay, cb, *args, **kwargs):
        """ Create a task that will be executed once after the given delay.

        Must be enabled first.

        Args:
            delay (float): Delay to the execution.
            cb (callable): Callable to call when timer fires.
            args (tuple): Positional arguments for callable.
            kwargs (dict): Keyword arguments for callable.
        Returns:
            Task: Created task.
        """

        t = Task(sched=self, delay=delay, cb=cb, repeat=False,
                 args=args, kwargs=kwargs)
        self.tasks.append(weakref.ref(t, self.tasks.remove))
        return t

    def idle(self, cb):
        """ Set idle callback.

        This callable will be executed when the scheduler has idle time.
        The idle time (in seconds, float) will be passed as first argument.
        The callable is expected to return after the idle time has passed.

        Args:
            cb (callable): Callable that will be executed on idle time.
        """

        self.idle_cb = cb

    def main(self, cb):
        """ Set main callback.

        The shell executed the scheduler with this main thread. GUIs that
        require the main thread can set a callable here that will get
        exclusive use of the main thread when the scheduler starts.
        The scheduler will shut down automatically after the callback returns.

        Args:
            cb (callable): Callable that will be executed with the main thread.
        """

        self.main_cb = cb
        self.main_changed.set()

    def shutdown(self):
        """ Shut down the scheduler.

        If main callback was set this has no effect until the callback returns.
        """

        self.shutdown_request.set()
        self.main_changed.set()

    def maintain(self):
        """ Perform scheduler option. """

        self.log.debug("Beginning to serve")
        tasks, max_sleep = self.tasks, self.max_sleep # Quick access

        while not self.shutdown_request.is_set():
            if self.tasks_changed:
                # Tasks changed, resort
                self.tasks_changed = False
                tasks.sort(key=lambda v: v())  # Tasks behind ref as key
            if not tasks or not tasks[0]():
                # No active tasks, just idle.
                self.idle_cb(max_sleep)
                continue

            # Get delay to next task.
            delay = min(max(0, self.delay_to(tasks[0]())), max_sleep)
            if delay > 0.01:
                # Idle if delay larger than 10 ms.
                self.idle_cb(delay)
            else:
                tasks[0]().fire()

    def run(self):
        """ Run scheduler.

        If main callback is set spawn an new thread for the scheduler and
        run it while calling the callback. If callback is not given run
        scheduler with this thread until shutdown request is set.
        """

        self.thread = threading.Thread(target=self.maintain,
                                       name="mauzr.sched")
        try:
            self.thread.start()
            while not self.shutdown_request.is_set():
                if callable(self.main_cb):
                    self.main_cb()
                else:
                    self.main_changed.wait()
                    self.main_changed.clear()
        finally:
            self.thread.join()
