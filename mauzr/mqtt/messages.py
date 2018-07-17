""" MQTT messages that are exchanged between an MQTT client and broker. """

from struct import pack, unpack

__author__ = "Alexander Sowitzki"

class Message(bytearray):  # pragma: no cover
    """ A message that can be sent to or received by an MQTT broker.

    Args:
        args (tuple): List of ints that is passed to the bytes constructor.
        kwargs (dict): Values of this dict are made available as attributes.
    """

    TYPE = None
    """ Packet type. """


    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.kwargs = kwargs

    def __getattr__(self, name):
        """ Get attributes given by constructor. """

        try:
            return self.kwargs[name]
        except KeyError as err:
            raise AttributeError(err)

    @staticmethod
    def pack_length(length):
        """ Pack the given length into a format understood by the MQTT broker.

        Args:
            length (int): Length to pack.
        Returns:
            bytes: Packed length.
        """

        assert length < 2097152
        buf = bytearray()
        while length != 0:
            ch = length % 128
            length //= 128
            if length > 0:
                ch |= 0x80
            buf.append(ch)
        return bytes(buf)


class Connect(Message):  # pragma: no cover
    """ Request a connection to the broker.

    Arguments for the constructor are:
    - will_topic (str): Topic for will message.
    - will_payload (bytes): Will message.
    - will_qos (int): QoS level for will message.
    - will_retain (bool): Will retainment flag.
    - clean_session (bool): Request clean session.
    - keepalive (int): Requested keepalive time.
    - user (str): User login name. Also used for client id.
    - passwd (str): User password
    """

    TYPE = 0x10

    def __init__(self, **kwargs):
        k = kwargs
        assert 0 <= k["will_qos"] <= 2
        cl_id, tp = k["id"].encode(), k["will_topic"].encode()
        pay = k["will_payload"]
        length = 10 + len(cl_id) + len(tp) + len(pay) + 5 * 2
        msg = bytearray(b"\x10" + self.pack_length(length))
        msg.extend(pack(">H4sB", 4, b"MQTT", 4))

        msg.append(k["will_retain"] << 5 | k["will_qos"] << 3 | True << 2 |
                   k["clean_session"] << 1)
        msg.extend(pack(">H", k["keepalive"]))
        for field in (cl_id, tp, pay):
            msg.extend(pack(">H", len(field)) + field)
        return super().__init__(msg, **kwargs)


class ConnAck(Message):  # pragma: no cover
    """ Connection acknoledgement from the broker.

    Attributes are:
    - session_cleared (bool): If session was cleared.
    """

    TYPE = 0x20

    def __init__(self, sock, op):
        if op != self.TYPE or sock.recv(1)[0] != 2:
            raise OSError("Invalid ConnAck message")
        flags, ret_code = sock.recv(2)
        if ret_code != 0:
            raise OSError(f"Connection error: {ret_code}")
        return super().__init__(session_cleared=flags & 1)

class Publish(Message):  # pragma: no cover
    """ Publish message. May be sent from broker and client.


    Attributes and constructor arguments:
    - topic (bool): Topic of the publish.
    - id (id): Publish ID.
    - payload (bytes): Publish payload.
    - qos (bool): QoS of the publish.
    - retain (bool): When sent to the broker this indicates if the message \
                     shall be retained. If sent by the broker True indicates \
                     that this message was retained and is not new.
    - duplicate (bool): If True this message was already sent at least once.

    Attributes only:
    - ack (PubAck): Acknoledgement that can be send to the server \
                    to ack this publish.
    - rec (PubRec): Acknoledgement that can be send to the server \
                    to mark this publish received.
    """

    TYPE = 0x30

    def __init__(self, *args, **kwargs):
        if args:
            sock, op = args
            assert op & 0xf0 == 0x30
            buf, sh = 0, 0
            while 1:
                b = sock.recv(1)[0]
                buf |= (b & 0x7f) << sh
                if not b & 0x80:
                    break
                sh += 7

            topic_len = unpack(">H", sock.recv(2))
            buf -= topic_len + 2
            info = {"topic": sock.recv(topic_len).decode(),
                    "id": None, "ack": None,
                    "qos": (op & 6) >> 1, "duplicate": op & 8,
                    "retained": op & 1}

            if info["qos"]:
                info["id"] = unpack(">H", sock.recv(2))
                if info["qos"] == 1:
                    info["ack"] = PubAck(id=info["id"])
                else:
                    info["rec"] = PubRec(id=info["id"])
                buf -= 2
            info["payload"] = sock.recv(buf)
            return super().__new__(**info)
        k = kwargs
        topic = k["topic"].encode()
        msg = bytearray([self.TYPE | k.get("duplicate", False) << 3 |
                         k["qos"] << 1 | k["retain"]])
        length = 2 + len(topic) + len(k["payload"]) + bool(k["qos"]) * 2
        msg.extend(self.pack_length(length))
        msg.extend(pack(">H", len(topic)) + topic)
        if k["qos"]:
            msg.extend(pack(">H", k["id"]))
        msg.extend(k["payload"])
        return super().__init__(msg, **kwargs)


class Subscribe(Message):  # pragma: no cover
    """ Subscribe to a topic.

    Arguments for the constructor are:
    - id (int): ID of the subscription message.
    - topic (str): Topic to subscribe to.
    - qos (int): QoS to subscribe with.
    """

    TYPE = 0x82

    def __init__(self, **kwargs):
        topic, qos, pkg_id = kwargs["topic"], kwargs["qos"], kwargs["id"]
        assert 0 <= qos <= 1
        topic = topic.encode()

        msg = bytearray([self.TYPE])
        msg.extend(self.pack_length(2 + 2 + len(topic) + 1))
        msg.extend(pack(">HH", pkg_id, len(topic)) + topic)
        msg.append(qos)
        return super().__init__(msg, **kwargs)


class SubAck(Message):  # pragma: no cover
    """ Broker acknowleges a subscription.

    Attributes are:
    - id (int): ID of the subscription.
    """

    TYPE = 0x90

    def __init__(self, sock, op):
        if op != self.TYPE or sock.recv(1)[0] != 3:
            raise OSError("Invalid SubAck message")

        sub_id = unpack(">H", sock.recv(2))[0]

        qos = sock.recv(1)[0]
        if qos not in (0, 1, 2):
            raise OSError(f"Subscription {sub_id} failed")
        return super().__init__(qos=qos, id=sub_id)


class Unsubscribe(Message):  # pragma: no cover
    """ Unsubscribe from a topic

    Arguments for the constructor are:
    - id (int): ID of the unsubscription message.
    - topic (str): Topic to unsubscribe from.
    """

    TYPE = 0xa2

    def __init__(self, **kwargs):
        k, msg = kwargs, bytearray([self.TYPE])
        topic = kwargs["topic"].encode()
        msg.extend(self.pack_length(2 + 2 + len(topic)))
        msg.extend(pack(">H", k["id"]))
        msg.extend(pack(">H", len(topic)) + topic)
        return super().__init__(msg, **kwargs)


class PingReq(Message):  # pragma: no cover
    """ Ping request sent from the client to the broker. """

    TYPE = 0xc0

    def __init__(self):
        return super().__init__([self.TYPE, 0])


class PingResp(Message):  # pragma: no cover
    """ Ping response sent from the broker to the client. """

    TYPE = 0xd0

    def __init__(self, sock, op):
        if op != self.TYPE or sock.recv(1)[0] != 0:
            raise OSError("Invalid PingResp Message")
        return super().__init__()


class Disconnect(Message):  # pragma: no cover
    """ Disconnect from the broker but publish the will message first.

    Arguments for the constructor are:
    - will_topic (str): Topic for will message.
    - will_payload (bytes): Will message.
    - will_qos (int): QoS level for will message.
    - will_retain (bool): Will retainment flag.
    - will_pkg_id (int): Message ID for the will message.
    """

    TYPE = 0xe0

    def __init__(self, **kwargs):
        k = kwargs
        msg = bytearray()
        msg.extend(Publish(topic=k["will_topic"], payload=k["will_payload"],
                           qos=k["will_qos"], retain=k["will_retain"],
                           id=k["will_pkg_id"]))
        msg.extend(bytes([self.TYPE, 0]))
        return super().__init__(msg, **kwargs)


class IDMessage(Message):  # pragma: no cover
    """ Base class for messages that only hold a package ID.

    Attributes are:
    - id (int): ID of the package.
    """

    def __init__(self, *args, **kwargs):
        if args:
            sock, op = args
            if op != self.TYPE or sock.recv(1)[0] != 2:
                raise OSError("Invalid message")
            return super().__new__(id=unpack(">H", sock.recv(2))[0])
        return super().__init__(pack(">BBH", self.TYPE, 2, kwargs["id"]))


class UnsubAck(Message):  # pragma: no cover
    """ Broker acknowleges an unsubscription.

    Attributes are:
    - id (int): ID of the unsubscription.
    """

    TYPE = 0xb0

    def __init__(self, sock, op):
        if op != self.TYPE or sock.recv(1)[0] != 2:
            raise OSError("Invalid UnsubAck message")
        pkg_id = unpack(">H", sock.recv(2))[0]
        return super().__init__(id=pkg_id)


class PubRec(IDMessage):  # pragma: no cover
    """ Publish received notification from the broker. """

    TYPE = 0x50


class PubRel(IDMessage):  # pragma: no cover
    """ Request to the broker to release publish. """

    TYPE = 0x62


class PubComp(IDMessage):  # pragma: no cover
    """ Confirmation from the server that the publish is completed. """

    TYPE = 0x70


class PubAck(IDMessage):  # pragma: no cover
    """ Acknowlege a publish. May be sent in both directions. """

    TYPE = 0x40
