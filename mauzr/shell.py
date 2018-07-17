""" Shell - Container and Manager for Agents. """

import contextlib
import logging
from argparse import ArgumentParser
from os import environ as env
from pathlib import Path
from mauzr.agent import AgentEvent as AE
from mauzr.mqtt.connector import Connector
from mauzr.scheduler import Scheduler

__author__ = "Alexander Sowitzki"


class AgentHandlerMixin:
    """ Mixin for handling agents. """

    def __init__(self, thin=False):
        self.agents = {}  # Agents of this shell.
        self.changed_agents = []  # Agents that changed and require update.
        self.agent_handle_task = self.sched.every(5, self.handle_agents)

        super().__init__(thin=thin)

    def apply_agent_event(self, agent, ev):
        """ Handle the change of a single agent.

        Args:
            agent (object): Agent that changed.
            ev (mauzr.AgentEvent): Event that caused the change.
        Returns:
            list: List containing tuples with agent and one event each that \
                  were generated while handling the change.
        """

        agents = self.agents
        if ev is AE.WANTS_CREATION:
            # Agent created - Add to list.
            agents[agent.name] = agent
        elif ev is AE.WANTS_DESTRUCTION:
            # Agent done - Destruct and remove from list.
            agent.discard()
            del agents[agent.name]
        elif ev is AE.WANTS_ACTIVATION and not agent.active and agent.ready:
            # Agent wants to be activated.
            agent.__enter__()
        elif ev in (AE.WANTS_DEACTIVATION, AE.WANTS_RESTART) and agent.active:
            # Agent wants to be disabled (or restarted).
            agent.__exit__(self, None, None, None)
            if ev is AE.WANTS_RESTART:
                # Schedule activation if needed.
                return [(agent, AE.WANTS_ACTIVATION)]
        return []

    def handle_agents(self):
        """ Handle agent changes. """

        events = [] # New events go here.
        while self.changed_agents:
            # Handle each changed agent.
            events.extend(self.apply_agent_event(*self.changed_agents.pop(0)))
        # Add new events to list.
        self.changed_agents.extend(events)

    def agent_changed(self, agent, event):
        """ Report that an agent has changed its state.

        Args:
            agent (object): Agent that changed.
            event (mauzr.AgentEvent): Event that caused the change.
        """

        self.changed_agents.append((agent, event))  # Put into list.

        # Force immediate agent handling if setup is done.
        if self.agent_handle_task:
            self.agent_handle_task.enable(instant=True)

    def __getattr__(self, name):
        """ Shortcut to receive agent of the shell.

        Args:
            name (str): Name of the agent.
        Returns:
            object: The agent if found.
        Raises:
            AttributeError: If agent not found.
        """

        try:
            return self.agents[name]
        except KeyError:
            raise AttributeError


class ParameterMixin:  # pragma: no cover
    """ Mixin that handles parameter gathering. """

    def __init__(self, thin=False, parser=None):
        if not parser:
            parser = ArgumentParser(description='Mauzr shell')
        # Fill parser with arguments.
        self._setup_arguments(parser)
        # Parse arguments.
        self.args = parser.parse_args()
        # Prepare data dir.
        self.args.data_path /= self.args.name
        self.args.data_path.mkdir(exist_ok=True)
        self.name = self.args.name

        super().__init__(thin=thin)

    @staticmethod
    def _setup_arguments(parser):  # pragma: no cover
        """ Define program arguments.

        Args:
            parser (argparse.ArgumentParser): Parser to use
        """

        arg = parser.add_argument
        arg('name', default=env.get('MAUZR_NAME'))
        arg('passwd', default=env.get('MAUZR_PASSWD'))
        arg('server', default=env.get('MAUZR_SERVER'))
        arg('ca', default=env.get('MAUZR_CA'))
        arg('--keepalive', default=env.get('MAUZR_KEEPALIVE', 60))
        arg('--backoff', default=env.get('MAUZR_BACKOFF', 10))
        arg('--max-sleep', default=env.get('MAUZR_MAX_SLEEP', 1))
        arg('--sync-interval', default=env.get('MAUZR_SYNC_INTERVAL', 60))
        arg('--log-level', default=env.get('MAUZR_LOG_LEVEL', "debug"))
        default = env.get('MAUZR_DATA_PATH', Path('/var/lib/mauzr'))
        arg('--data-path', default=default, type=Path)

class CoreComponentMixin:  # pragma: no cover
    """ Mixin to provide core components to the shell. """

    def __init__(self, thin=False):
        # Setup root logger.
        self.log = logging.getLogger(self.args.name)
        self.log.setLevel(logging.getLevelName(self.args.log_level.upper()))
        self.log.debug("Logger created")

        # Setup scheduler and MQTT.
        self.sched = Scheduler(self)
        self.mqtt = Connector(self)

        super().__init__(thin=thin)


class InitiatorMixin:  # pragma: no cover
    """ Mixin that handles initiation of the shell. """

    def __init__(self, thin=False):

        if not thin:
            from mauzr.agents.logger import LogSender
            from mauzr.agents.spawner import AgentSpawner
            # Add agent spawner.
            spawner = AgentSpawner(self, "spawner")
            # Spawn optional agents.
            spawner.spawn_agent(LogSender, "logger")
            if 'NOTIFY_SOCKET' in env:
                from mauzr.agents.systemd import Systemd
                spawner.spawn_agent(Systemd, "systemd")
        self.log.debug("Setup done")
        super().__init__()

    def run(self):
        """ Block and run the shell. """

        self.log.debug("Starting mqtt")
        # MQTT is required for everything following.
        with self.mqtt:
            try:
                # Go directly into scheduler.
                self.log.debug("Passing to scheduler")
                self.sched.run()
            finally:
                # Discard all remaining agents.
                [agent.discard() for agent in self.agents.values()]
                self.agents = None
                self.changed_agents = None


class Shell(ParameterMixin, CoreComponentMixin,
            AgentHandlerMixin, InitiatorMixin):
    """ Container and manager for agents.

    This class fetches information required to provide MQTT connectivity
    via program arguments and spawn core components.

    Args:
        thin (bool): If True, core components are not spawned.
        parser (argparse.ArgumentParser): Will be used instead of an empty \
                                          parser if set.
    """


def main():  # pragma: no cover
    """ Program entry method.

    Sets up logging and starts shell.
    """

    logging.basicConfig()
    with contextlib.suppress(KeyboardInterrupt):
        Shell().run()

if __name__ == "__main__":  # pragma: no cover
    main()
