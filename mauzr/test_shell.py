""" Test shell module. """

import logging
import unittest
from unittest.mock import Mock
from mauzr.agent import AgentEvent as AE
from mauzr.shell import AgentHandlerMixin

__author__ = "Alexander Sowitzki"

class AgentHandlerMixinTest(unittest.TestCase):
    """ Test shell class. """

    def test_all(self):
        """ Test all. """

        # pylint: disable=too-many-statements

        class _Lower:
            def __init__(self, thin):
                pass

        class _TestClass(AgentHandlerMixin, _Lower):
            def __init__(self, thin):
                self.name = "testshell"
                self.sched = Mock()
                self.log = logging.getLogger()
                super().__init__(thin=thin)

        agent = Mock(spec_set=["__enter__", "__exit__",
                               "name", "active", "ready", "discard"],
                     active=False, ready=True)
        agent.name = "testagent"
        agent.__enter__ = Mock()
        agent.__exit__ = Mock()

        shell = _TestClass(thin=True)
        shell.sched.every.assert_called_once_with(5, shell.handle_agents)
        task = shell.sched.every()
        task.enable.assert_not_called()
        task.enable.reset_mock()
        self.assertFalse(shell.changed_agents)
        shell.handle_agents()
        self.assertFalse(shell.agents)
        self.assertFalse(shell.changed_agents)
        shell.agent_changed(agent, AE.WANTS_CREATION)
        task.enable.assert_called_once_with(instant=True)
        task.enable.reset_mock()
        shell.agent_changed(agent, AE.WANTS_DEACTIVATION)
        task.enable.assert_called_once_with(instant=True)
        task.enable.reset_mock()
        self.assertEqual(2, len(shell.changed_agents))
        shell.handle_agents()
        self.assertEqual(agent, shell.agents[agent.name])
        self.assertIs(agent, getattr(shell, agent.name))
        self.assertRaises(AttributeError, getattr, shell, "something")
        agent.__enter__.assert_not_called()
        agent.__exit__.assert_not_called()
        shell.agent_changed(agent, AE.WANTS_ACTIVATION)
        shell.handle_agents()
        agent.active = True
        agent.__enter__.assert_called_once_with()
        agent.__exit__.assert_not_called()
        agent.__enter__.reset_mock()
        agent.__exit__.reset_mock()
        shell.agent_changed(agent, AE.WANTS_RESTART)
        shell.handle_agents()
        agent.active = False
        agent.__enter__.assert_not_called()
        agent.__exit__.assert_called_once()
        agent.__exit__.reset_mock()
        shell.handle_agents()
        agent.active = True
        agent.__exit__.assert_not_called()
        agent.__enter__.assert_called_once_with()
        agent.__enter__.reset_mock()
        shell.agent_changed(agent, AE.WANTS_DESTRUCTION)
        shell.handle_agents()
        self.assertFalse(shell.agents)
        agent.__enter__.assert_not_called()
        agent.__exit__.assert_not_called()
