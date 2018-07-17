""" MQTT errors. """

__author__ = "Alexander Sowitzki"

class MQTTError(OSError):
    """ Base for all MQTT errors. """


class MQTTOfflineError(MQTTError):
    """ Indicates communication was attempted while offline. """

    def __init__(self, message=None):  # pragma: no cover
        super().__init__()
        self.message = message


class MQTTProtocolError(MQTTError):
    """ Indicates that the broker responded illegal. """
