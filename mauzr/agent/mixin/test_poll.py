""" Agent mixins test. """

from unittest.mock import call
from mauzr.agent import Agent
from mauzr.agent import AgentEvent as AE
from mauzr.agent.mixin.poll import PollMixin
from mauzr.agent.test_agent import AgentTest

class _TestAgent(Agent, PollMixin):
    # pylint: disable=abstract-method
    pass

class PollingAgentTest(AgentTest):
    """ Test PollMixin class. """

    AgentClass = _TestAgent

    def ready_agent(self, agent):
        """ Ready the given agent. """

        agent_changed = agent.shell.agent_changed

        self.assertEqual(2, agent_changed.call_count)
        agent_changed.assert_has_calls([call(agent, AE.WANTS_CREATION),
                                        call(agent, AE.WANTS_DEACTIVATION)])
        agent.shell.agent_changed.reset_mock()
        topic = f"cfg/{agent.shell.name}/{agent.name}/log_level"
        agent.shell.handles[topic].sub.call_args[0][0]("info")
        topic = f"cfg/{agent.shell.name}/{agent.name}/interval"
        agent.shell.handles[topic].sub.call_args[0][0](0.5)
        agent_changed.assert_has_calls([call(agent, AE.WANTS_DEACTIVATION),
                                        call(agent, AE.WANTS_ACTIVATION)])
        agent_changed.reset_mock()

    def test_polling(self):
        """ Test PollMixin operations. """

        agent_name = "TestAgent"
        shell = self.shell_mock(agent_name)
        agent = _TestAgent(shell, agent_name)
        shell.sched.every.assert_called_once()
        prefix = f"cfg/testshell/{agent_name}/"

        agent_changed = agent.shell.agent_changed

        self.assertEqual(2, agent_changed.call_count)
        agent_changed.assert_has_calls([call(agent, AE.WANTS_CREATION),
                                        call(agent, AE.WANTS_DEACTIVATION)])
        agent_changed.reset_mock()
        topic = f"cfg/{agent.shell.name}/{agent.name}/log_level"
        agent.shell.handles[topic].sub.call_args[0][0]("info")
        agent_changed.assert_not_called()

        self.assertFalse(agent.ready)
        self.assertRaises(NotImplementedError, agent.poll)
        agent.poll_task.set.assert_not_called()
        agent.poll_task.enable.assert_not_called()
        agent.poll_task.disable.assert_not_called()

        delay = 0.5
        print(shell.handles)
        print(prefix+"interval")
        shell.handles[prefix+"interval"].sub.call_args[0][0](delay)
        agent.poll_task.set.assert_called_once_with(delay)
        self.assertTrue(agent.ready)

        with agent:
            agent.poll_task.enable.assert_called_once()
            agent.poll_task.disable.assert_not_called()
        agent.poll_task.enable.assert_called_once()
        agent.poll_task.disable.assert_called_once()
        shell.sched.every.assert_called_once()
