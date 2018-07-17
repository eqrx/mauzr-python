""" Agent spawning. """

import importlib
from mauzr.agent import Agent, AgentEvent
from mauzr.serializer import String

__author__ = "Alexander Sowitzki"


class AgentSpawner(Agent):
    """ Spawns other agents into the shell.

    This agents subscribes right below the shell configuration topic
    and receives the names and call paths of new agents.
    These agents are created and started.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        handle = self.shell.mqtt(topic=f"cfg/{self.shell.name}/+",
                                 ser=String("Agent path to load"),
                                 qos=1, retain=True)
        self.static_input(handle, self.on_agent,
                          sub={"handle": True})

    def on_agent(self, path, topic):
        """ Takes agent path and name and spawns the agent.

        Args:
            path (str): Path to the callable that spawns an agent.
            topic (Handle): The handle that received the path.
        """

        shell, log = self.shell, self.log

        # Get agent path parts.
        if path.count(":") != 1:
            log.error("Invalid agent path: %s", path)
            return
        module_name, call_name = path.split(":")

        name = topic.chunks[-1]  # Agent name is last level of its topic.

        if path == "":
            # Path is empty -> Agent needs to be removed
            shell.agent_changed(shell[name], AgentEvent.WANTS_DESTRUCTION)
            return

        # Import agent module.
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            log.error("Agent module could not be loaded: %s", module_name)
            return

        # Get factory method.
        factory = getattr(module, call_name)
        if not callable(factory):
            log.error("Agent factory %s is not callable", factory)
            return

        # Spawn agent.
        agent = factory(self.shell, name)

        if not isinstance(agent, Agent):
            log.error(f"Factory {factory} did not spawn an agent but {agent}")
