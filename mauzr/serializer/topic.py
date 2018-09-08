""" Serializers for topic information. """

import json
from .base import Serializer, SerializationError

__author__ = "Alexander Sowitzki"

class Topic(Serializer):
    """ Serializer for topic information.

    Args:
        shell (mauzr.shell.Shell): Program shell.
        desc (str): Topic description.
    """

    fmt = "topic"

    @staticmethod
    def pack(h):
        """ Pack topic handle into JSON string.

        Args:
            h (mauzr.mqtt.Handle): Handle to serialize.
        Returns:
            bytes: Serialized topic information as JSON string.
        Raises:
            SerializationError: On error.
        """

        if h is None:
            return bytes()
        if isinstance(h, dict):
            if set(("topic", "qos", "retain", "fmt")).issubset(set(h.keys())):
                return json.dumps(h).encode()
            raise SerializationError(f"Invalid topic information: {h}")
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

        if not data:
            return None

        try:
            j = json.loads(data.decode())
        except json.JSONDecodeError as err:
            raise SerializationError(err)
        ser = self.from_well_known(shell=self.shell,
                                   fmt=j["fmt"], desc=self.desc)
        return self.shell.mqtt(topic=j["topic"], ser=ser,
                               qos=j["qos"], retain=j["retain"])

class Topics(Serializer):
    """ Serializer for a list of topic information.

    Args:
        shell (mauzr.shell.Shell): Program shell.
        desc (str): Description of the topic list.
    """

    fmt = "topics"

    @staticmethod
    def pack(handles):
        """ Pack topic handle into JSON string.

        Args:
            handles (list): Handles to serialize.
        Returns:
            bytes: Serialized topic information as JSON string.
        Raises:
            SerializationError: On error.
        """

        if handles is None:
            return bytes()

        data = []
        for h in handles:
            if isinstance(h, dict):
                k = set(("topic", "qos", "retain", "fmt"))
                if k.issubset(set(h.keys())):
                    data.append(h)
                else:
                    raise SerializationError(f"Invalid topic information: {h}")
            else:
                data.append({"topic": h.topic, "qos": h.qos,
                             "retain": h.retain, "fmt": h.ser.fmt})

        return json.dumps(data).encode()

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
                                ser=self.from_well_known(shell=self.shell,
                                                         fmt=i["fmt"],
                                                         desc=self.desc),
                                qos=i["qos"], retain=i["retain"]) for i in j]
