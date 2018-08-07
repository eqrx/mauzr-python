""" Shell - Container and Manager for Agents. """

import sys
import signal
import weakref
import time
from contextlib import suppress
import logging
from argparse import ArgumentParser
from os import environ as env
from pathlib import Path
from mauzr.mqtt.connector import Connector
from mauzr.scheduler import Scheduler

__author__ = "Alexander Sowitzki"


class AgentHandlerMixin:
    """ Mixin for handling agents. """

    def __init__(self, thin=False):
        self.agents = weakref.WeakValueDictionary()  # Agents of this shell.
        self.agent_listeners = weakref.WeakSet()

        super().__init__(thin=thin)

    def add_agent_listener(self, cb):
        """ Add a listener for agent changes.

        Args:
            cb (callable): Listener that will be called with the agent and event
        """

        self.agent_listeners.add(cb)

    def add_agent(self, agent):
        """ Add a new agent to the shell.

        Args:
            agent (mauzr.Agent): New agent.
        Raises:
            KeyError: If agent already present.
        """

        if agent.name in self.agents:
            raise KeyError(f"Agent {agent.name} is already present")
        self.agents[agent.name] = agent

    def fire_agent_listeners(self, name):
        """ Fire agent listeners.

        Args:
            name (str): Name that will be passed.
        """

        [cb(name) for cb in self.agent_listeners]

    def shutdown_agents(self):
        """ Shutdown all present agents. """

        with suppress(KeyError):
            self.agents["spawner"].update_agent(discard=True)
        for a in self.agents.values():
            a.update_agent(discard=True)
        time.sleep(1)


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
        arg('--name', default=env.get('MAUZR_NAME'))
        arg('--domain', default=env.get('MAUZR_DOMAIN'))
        arg('--key', default=env.get('MAUZR_KEY'))
        arg('--crt', default=env.get('MAUZR_CRT'))
        arg('--ca', default=env.get('MAUZR_CA'))
        arg('--keepalive', default=env.get('MAUZR_KEEPALIVE', 60))
        arg('--backoff', default=env.get('MAUZR_BACKOFF', 10))
        arg('--max-sleep', default=env.get('MAUZR_MAX_SLEEP', 1))
        arg('--sync-interval', default=env.get('MAUZR_SYNC_INTERVAL', 60))
        arg('--log-level', default=env.get('MAUZR_LOG_LEVEL', "info"))
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
        self.mqtt.__enter__()

        super().__init__(thin=thin)

    def shutdown(self):
        """ Shuts down the shell gracefully. """

        self.shutdown_agents()
        self.mqtt.__exit__()
        self.sched.shutdown()

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
        try:
            # Go directly into scheduler.
            self.log.debug("Passing to scheduler")
            self.sched.run()
        finally:
            self.shutdown()


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

    def sigterm_handler(_signo, _stack_frame):
        sys.exit(0)
    signal.signal(signal.SIGTERM, sigterm_handler)

    logging.basicConfig(format='%(name)s: %(message)s')
    with suppress(KeyboardInterrupt):
        Shell().run()

if __name__ == "__main__":  # pragma: no cover
    main()
