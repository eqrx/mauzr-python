""" Controller for linux audio drivers."""
__author__ = "Alexander Sowitzki"

import mauzr.platform.serializer

class Controller:
    """ Manage :class:`mauzr.linux.audio.linker.Linker` over the network.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units**:

        - mqtt

    **Configuration:**

        - **base** (:class:`str`) - Base for topics.

    **Output topics:**

        - **/say** (:class:`str`) - Say a given text on target device.
        - **/play** (:class:`str`) - Play a file under the given path
                                     on target device.
    """

    def __init__(self, core, cfgbase="audio", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._mqtt = core.mqtt
        self._base = cfg["base"]
        core.mqtt.setup_publish(self._base + "play",
                                mauzr.platform.serializer.String, 0)
        core.mqtt.setup_publish(self._base + "say",
                                mauzr.platform.serializer.String, 0)

    def play(self, path):
        """ Play a file on the driver device.

        :param path: File path on the host.
        :type path: str
        """

        self._mqtt.publish(self._base + "play", path, False)

    def say(self, text):
        """ Dispatch a text to the speech dispatcher.

        :param text: Text to speak.
        :type text: str
        """

        self._mqtt.publish(self._base + "say", text, False)
