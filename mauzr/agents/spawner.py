""" Agent spawning. """

import importlib
from contextlib import suppress
from mauzr.agent import Agent
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
        self.update_agent(arm=True)

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
            log.error("Factory %s did not spawn an agent but %s",
                      factory, agent)
        log.info("Agent spawned: %s -> %s", agent.name, str(factory))

    def on_agent(self, path, handle):
        """ Takes agent path and name and spawns the agent.

        Args:
            path (str): Factory path.
            handle (Handle): The handle that received the path.
        """

        shell, log = self.shell, self.log
        name = handle.chunks[-1]  # Agent name is last level of its topic.
        assert name != '+', f"Agent path invalid {handle.topic}"

        if name in self.shell.agents:
            self.log.warning("Agent %s with %s already present", name, path)
            return

        if not path:
            # Path is empty -> Agent needs to be removed
            with suppress(KeyError):
                shell.agents[name].update_agent(discard=True)
                log.info("Agent cleared: %s", name)
            return

        # Get agent path parts.
        if path.count(":") != 1:
            log.error("Invalid agent path: %s", path)
            return
        module_name, call_name = path.split(":")

        # Import agent module.
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            log.error("Agent module could not be loaded: %s", module_name)
            return

        # Get factory method.
        try:
            factory = getattr(module, call_name)
        except AttributeError:
            log.error("Agent module %s does not contain %s factory",
                      module_name, call_name)
            return

        self.spawn_agent(factory, name)
