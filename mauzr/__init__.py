""" Factories for platform specific core implementations. """

__author__ = "Alexander Sowitzki"


def _bootstrap(core, unit):
    if unit is not None:
        unit(core)
        core.run()
    return core


def cpython(suit, agent, unit=None, instance=None, parser=None):
    """ Create core for cpython.

    :param suit: Suit this agent belongs to.
    :type suit: str
    :param agent: Name of the agent.
    :type agent: str
    :param unit: Unit to launch. It receives the core as argument.
    :type unit: callable
    :param instance: Instance of this agent. May be None
    :type instance: str
    :param parser: Argparse instance to use. If None, a new one will be used.
    :type parser: argparse.ArgumentParser
    :returns: Core instance.
    :rtype: mauzr.platform.linux.Core
    """

    from mauzr.platform.cpython import Core
    return _bootstrap(Core(suit, agent, instance, parser), unit)


def linux(suit, agent, unit=None, instance=None, parser=None):
    """ Create core for linux.

    :param suit: Suit this agent belongs to.
    :type suit: str
    :param agent: Name of the agent.
    :type agent: str
    :param unit: Unit to launch. It receives the core as argument.
    :type unit: callable
    :param instance: Instance of this agent. May be None
    :type instance: str
    :param parser: Argparse instance to use. If None, a new one will be used.
    :type parser: argparse.ArgumentParser
    :returns: Core instance.
    :rtype: mauzr.platform.linux.Core
    """

    from mauzr.platform.linux import Core
    return _bootstrap(Core(suit, agent, instance, parser), unit)


def docker(suit, agent, unit=None, instance=None, parser=None):
    """ Create core for docker.

    :param suit: Suit this agent belongs to.
    :type suit: str
    :param agent: Name of the agent.
    :type agent: str
    :param unit: Unit to launch. It receives the core as argument.
    :type unit: callable
    :param instance: Instance of this agent. May be None
    :type instance: str
    :param parser: Argparse instance to use. If None, a new one will be used.
    :type parser: argparse.ArgumentParser
    :returns: Core instance.
    :rtype: mauzr.platform.docker.Core
    """

    from mauzr.platform.docker import Core
    return _bootstrap(Core(suit, agent, instance, parser), unit)
