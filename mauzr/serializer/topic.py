""" Serializers for topic information. """

import json
from .base import Serializer, SerializationError

# TODO use SerializationError

__author__ = "Alexander Sowitzki"

class Topic(Serializer):
    """ Serializer for topic information.

    Args:
        shell (mauzr.shell.Shell): Program shell.
        desc (str): Topic description.
    """

    fmt = "topic"

    def __init__(self, shell, desc):
        super().__init__(desc)
        self.shell = shell

    @staticmethod
    def pack(h):
        """ Pack topic handle into JSON string.

        Args:
            h (mauzr.mqtt.Handle): Handle to serialize.
        Returns:
            bytes: Serialized topic information as JSON string.
        """

        if h is None:
            return bytes()

        return json.dumps({"topic": h.topic, "qos": h.qos,
                           "retain": h.retain, "fmt": h.ser.fmt}).encode()

    def unpack(self, data):
        """ Unpack topic information and create handle for it.

        Args:
            data (bytes): Topic information as JSON string.
        Returns:
            mauzr.mqtt.Handle: Handle for the given topic information.
        Raises:
            SerializationError: On error.
        """

        try:
            j = json.loads(data.decode())
        except json.JSONDecodeError as err:
            raise SerializationError(err)
        ser = self.from_well_known(j["fmt"], self.desc)
        return self.shell.mqtt(topic=j["topic"], ser=ser,
                               qos=j["qos"], retain=j["retain"])

class Topics(Serializer):
    """ Serializer for a list of topic information.

    Args:
        shell (mauzr.shell.Shell): Program shell.
        desc (str): Description of the topic list.
    """

    fmt = "topics"

    def __init__(self, shell, desc):
        super().__init__(desc)
        self.shell = shell

    @staticmethod
    def pack(handles):
        """ Pack topic handle into JSON string.

        Args:
            handles (list): Handles to serialize.
        Returns:
            bytes: Serialized topic information as JSON string.
        """

        if handles is None:
            return bytes()

        topics = [{"topic": h.topic, "qos": h.qos,
                   "retain": h.retain, "fmt": h.ser.fmt} for h in handles]

        return json.dumps(topics).encode()

    def unpack(self, data):
        """ Unpack a list of topic information and create handles for it.

        Args:
            data (bytes): Topic information as JSON string.
        Returns:
            list: Handles for given topics.
        Raises:
            SerializationError: On error.
        """

        try:
            j = json.loads(data.decode())
        except json.JSONDecodeError as err:
            raise SerializationError(err)

        return [self.shell.mqtt(topic=i["topic"],
                                ser=self.from_well_known(i["fmt"], self.desc),
                                qos=i["qos"], retain=i["retain"]) for i in j]
