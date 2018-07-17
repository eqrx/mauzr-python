""" Test scheduler. """

import time
import logging
import unittest
from unittest.mock import Mock, NonCallableMock
from mauzr.scheduler import Task, Scheduler

__author__ = "Alexander Sowitzki"

class SchedulerTest(unittest.TestCase):
    """ Test Scheduler class. """

    @staticmethod
    def shell_mock():
        """ Create shell mock. """

        return NonCallableMock(spec_set=["log", "args"],
                               log=logging.getLogger(),
                               args=NonCallableMock(spec_set=["max_sleep"],
                                                    max_sleep=1.0))

    def test_delay_to(self):
        """ Test delay_to method. """

        task = NonCallableMock(spec_set=["at", "time_func"], at=3,
                               time_func=Mock(spec_set=[""], return_value=2))
        self.assertEqual(1, Scheduler.delay_to(task))

    def test_task_creation(self):
        """ Test the creation of tasks. """

        shell = self.shell_mock()
        sched = Scheduler(shell)

        args = (1, 2)
        kwargs = {"3": True, "4": False}
        delay = 3
        cb = Mock(spec_set=[])
        task = sched.every(delay, cb, *args, **kwargs)
        self.assertIs(cb, task.cb)
        self.assertIs(delay, task.delay)
        self.assertEqual(args, task.args)
        self.assertEqual(kwargs, task.kwargs)
        self.assertTrue(task.repeat)
        task = sched.after(delay, cb, *args, **kwargs)
        self.assertIs(cb, task.cb)
        self.assertIs(delay, task.delay)
        self.assertEqual(args, task.args)
        self.assertEqual(kwargs, task.kwargs)
        self.assertFalse(task.repeat)

    def test_maintain(self):
        """ Test maintain functions. """

        shell = self.shell_mock()
        max_sleep = 1337
        shell.args.max_sleep = max_sleep
        sched = Scheduler(shell)
        times = [0, 0, 20, 1, 2, 2, 20]

        self.assertFalse(sched.tasks_changed)

        time_func = Mock(spec_set=[], side_effect=times)

        calls = []
        def _cb(delay):
            calls.append(delay)

        delays = [1, 2, 4]

        def _idle(delay):
            if delay == max_sleep:
                sched.shutdown()
        sched.idle(_idle)

        tasks = [sched.after(delay, _cb, delay)
                 for delay in delays]
        self.assertFalse(sched.tasks_changed)
        for task in tasks:
            task.time_func = time_func
            task.enable(instant=True)
        self.assertTrue(sched.tasks_changed)
        self.assertFalse(calls)
        sched.maintain()
        self.assertFalse(sched.tasks_changed)
        self.assertEqual(delays, calls)

    def test_task_cleanup(self):
        """ Test cleanup of tasks. """

        shell = self.shell_mock()
        sched = Scheduler(shell)

        args = (1, 2)
        kwargs = {"3": True, "4": False}
        delay = 3
        cb = Mock(spec_set=[])
        task = sched.every(delay, cb, *args, **kwargs)
        task.enable()
        self.assertEqual(1, len(sched.tasks))
        del task
        self.assertEqual(0, len(sched.tasks))

    def test_run(self):
        """ Test run method. """

        shell = self.shell_mock()
        sched = Scheduler(shell)
        main = Mock(spec_set=[], side_effect=sched.shutdown)
        def _side():
            time.sleep(0.001)
            sched.main(main)
        maintain = Mock(spec_set=[], side_effect=_side)

        sched.maintain = maintain
        sched.run()
        sched.maintain.assert_called_once_with()
        main.assert_called_once_with()


class TaskTest(unittest.TestCase):
    """ Test Task class. """

    def test_time(self):
        """ Test time handling. """

        sched = NonCallableMock(spec_set=["tasks_changed"])
        args = (1, 2)
        kwargs = {"3": True, "4": False}
        delay1, delay2 = 1, 2
        times = [4, 8, 16, 32]
        cb1, cb2 = Mock(spec_set=[]), Mock(spec_set=[])
        time_func = Mock(spec_set=[], side_effect=times)
        task1 = Task(sched=sched, delay=delay1, repeat=False, cb=cb1,
                     args=args, kwargs=kwargs)
        task1.time_func = time_func
        task2 = Task(sched=sched, delay=delay2, repeat=False, cb=cb2,
                     args=args, kwargs=kwargs)
        task2.time_func = time_func

        self.assertIsNone(task1.at)
        self.assertIsNone(task2.at)
        task1.enable()
        self.assertEqual(delay1+times[0], task1.at)
        task2.enable(instant=True)
        self.assertEqual(times[1], task2.at)

    def test_fire(self):
        """ Test task firing. """

        sched = NonCallableMock(spec_set=["tasks_changed"])
        args = (1, 2)
        kwargs = {"3": True, "4": False}
        delay = 1
        times = [4, 8, 16, 32]
        cb = Mock(spec_set=[])
        time_func = Mock(spec_set=[], side_effect=times)
        task = Task(sched=sched, delay=delay, repeat=False, cb=cb,
                    args=args, kwargs=kwargs)
        task.time_func = time_func

        self.assertRaises(RuntimeError, task.fire)
        task.enable()
        self.assertTrue(task)
        cb.assert_not_called()
        task.fire()
        cb.assert_called_once_with(*args, **kwargs)
        cb.reset_mock()
        self.assertFalse(task)
        task.repeat = True
        task.enable()
        task.fire()
        cb.assert_called_once_with(*args, **kwargs)
        self.assertTrue(task)
        self.assertEqual(delay+times[2], task.at)

    def test_aus(self):
        """ Test __lt__ and __bool__. """

        sched = NonCallableMock(spec_set=["tasks_changed"])
        args = (1, 2)
        kwargs = {"3": True, "4": False}
        delay1, delay2 = 0.003, 0.010
        cb1, cb2 = Mock(spec_set=[]), Mock(spec_set=[])
        task1 = Task(sched=sched, delay=delay1, repeat=False, cb=cb1,
                     args=args, kwargs=kwargs)
        task2 = Task(sched=sched, delay=delay2, repeat=False, cb=cb2,
                     args=args, kwargs=kwargs)

        self.assertFalse(task1)
        self.assertFalse(task2)
        self.assertFalse(task1 < task1)
        self.assertFalse(task2 < task2)
        self.assertFalse(task2 < task1)
        self.assertFalse(task1 < task2)

        task1.enable()

        self.assertTrue(task1)
        self.assertFalse(task2)
        self.assertFalse(task1 < task1)
        self.assertFalse(task2 < task2)
        self.assertFalse(task2 < task1)
        self.assertTrue(task1 < task2)

        task2.enable()

        self.assertTrue(task1)
        self.assertTrue(task2)
        self.assertFalse(task1 < task1)
        self.assertFalse(task2 < task2)
        self.assertFalse(task2 < task1)
        self.assertTrue(task1 < task2)

        task2.enable(instant=True)

        self.assertTrue(task1)
        self.assertTrue(task2)
        self.assertTrue(task2 < task1)
        self.assertFalse(task1 < task2)

        task2.disable()

        self.assertTrue(task1)
        self.assertFalse(task2)
        self.assertFalse(task1 < task1)
        self.assertFalse(task2 < task2)
        self.assertFalse(task2 < task1)
        self.assertTrue(task1 < task2)
