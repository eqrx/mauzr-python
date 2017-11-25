""" Factories for platform specific core implementations. """
__author__ = "Alexander Sowitzki"

def cpython(suit, agent, instance=None, parser=None):
    """ Create core for cpython.

    :param suit: Suit this agent belongs to.
    :type suit: str
    :param agent: Name of the agent.
    :type agent: str
    :param instance: Instance of this agent. May be None
    :type instance: str
    :param parser: Argparse instance to use. If None, a new one will be used.
    :type parser: argparse.ArgumentParser
    :returns: Core instance.
    :rtype: mauzr.platform.linux.Core
    """

    from mauzr.platform.cpython import Core
    return Core(suit, agent, instance, parser)

def linux(suit, agent, instance=None, parser=None):
    """ Create core for linux.

    :param suit: Suit this agent belongs to.
    :type suit: str
    :param agent: Name of the agent.
    :type agent: str
    :param instance: Instance of this agent. May be None
    :type instance: str
    :param parser: Argparse instance to use. If None, a new one will be used.
    :type parser: argparse.ArgumentParser
    :returns: Core instance.
    :rtype: mauzr.platform.linux.Core
    """

    from mauzr.platform.linux import Core
    return Core(suit, agent, instance, parser)

def docker(suit, agent, instance=None, parser=None):
    """ Create core for docker.

    :param suit: Suit this agent belongs to.
    :type suit: str
    :param agent: Name of the agent.
    :type agent: str
    :param instance: Instance of this agent. May be None
    :type instance: str
    :param parser: Argparse instance to use. If None, a new one will be used.
    :type parser: argparse.ArgumentParser
    :returns: Core instance.
    :rtype: mauzr.platform.docker.Core
    """

    from mauzr.platform.docker import Core
    return Core(suit, agent, instance, parser)
