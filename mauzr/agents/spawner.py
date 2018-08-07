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
                                 ser=String(shell=self.shell,
                                            desc="Agent path to load"),
                                 qos=1, retain=True)
        self.static_input(handle, self.on_agent,
                          sub={"wants_handle": True})

    def spawn_agent(self, factory, name):
        """ Spawn a given agent.

        Args:
            factory (callable): Factory method for the agent.
            name (str): Name the agent is registered under.
        """

        assert name != '+'

        shell, log = self.shell, self.log

        if not callable(factory):
            log.error("Agent factory %s is not callable", factory)
            return

        # Spawn agent.
        agent = factory(shell, name)

        if not isinstance(agent, Agent):
            log.error(f"Factory {factory} did not spawn an agent but {agent}")

    def on_agent(self, value, handle):
        """ Takes agent path and name and spawns the agent.

        Args:
            value (object): Ignored.
            handle (Handle): The handle that received the path.
        """

        shell, log = self.shell, self.log

        path = value

        # Get agent path parts.
        if path.count(":") != 1:
            log.error("Invalid agent path: %s", path)
            return
        module_name, call_name = path.split(":")

        name = handle.chunks[-1]  # Agent name is last level of its topic.
        assert name != '+'

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
        self.spawn_agent(factory, name)
