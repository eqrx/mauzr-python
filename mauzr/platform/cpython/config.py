""" Configuration helper. """

import logging

__author__ = "Alexander Sowitzki"


class Config:
    """ Load and parse configuration for posix agents.

    :param suit: Suit this agent belongs to.
    :type suit: str
    :param agent: Name of the agent.
    :type agent: str
    :param instance: Instance of this agent. May be None
    :type instance: str
    :param parser: Argparse instance to use. If None, a new one will be used.
    :type parser: argparse.ArgumentParser
    """

    def __init__(self, suit, agent, instance=None, parser=None):

        self.parser = parser
        if parser is None:
            import argparse
            self.parser = argparse.ArgumentParser()
        self.parser.add_argument("--systemd", action="store_true",
                                 help="Systemd integration")
        self.parser.add_argument("--log-level", default="info",
                                 help="Log level")
        self._args = None
        self._config = None
        self.id = [suit, agent]
        if instance is not None:
            self.id.append(instance)
        else:
            self.parser.add_argument("-i", "--instance", required=False,
                                     help="Instance name")

        self._log = logging.getLogger("<Config>")

    def __contains__(self, key):
        return hasattr(self._args, key) or key in self._config

    def __getitem__(self, key):
        if hasattr(self._args, key):
            return getattr(self._args, key)
        elif key in self._config:
            return self._config[key]
        self._config[key] = {}
        return self._config[key]

    def __setitem__(self, key, value):
        self._config[key] = value

    def get(self, *args):
        """ See :func:`dict.get`. """

        key = args[0]
        if len(args) == 1:
            return self[key]
        return self[key] if key in self else args[1]

    def read_config(self):
        """ Find and read yaml configuration. """

        import os.path
        import yaml
        import glob
        home = os.path.expanduser("~")
        path_canidates = [".mauzr.conf",
                          "{}.config/mauzr.conf".format(home),
                          "/etc/mauzr.conf", "/run/secrets/mauzr.conf"]
        path_canidates += glob.glob("/etc/mauzr.d/*.conf")

        id_str = "-".join(self.id)

        for candidate in path_canidates:
            try:
                data = open(candidate, "r").read()
            except IOError:
                self._log.debug("Config file %s could not be opened",
                                candidate)
                continue

            self._config = yaml.load(data)
            if not self._config or id_str not in self._config:
                self._log.debug("Config file %s does not"
                                " contain entry for %s", candidate, id_str)
                continue

            self._config = self._config[id_str]
            break
        else:
            self._log.debug("No config file found for %s", id_str)
            self._config = {}

        self._config["id"] = self.id
        return self._config

    def parse(self):
        """ Parse arguments and configuration. """

        self._args = self.parser.parse_args()
        if "instance" in self._args and self._args.instance is not None:
            if len(self.id) != 2:
                raise ValueError("Instance was already set by agent. "
                                 "Overriding not allowed.")
            self.id.append(self._args.instance)
        self.read_config()
