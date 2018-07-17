""" Basicics serializers. """

__author__ = "Alexander Sowitzki"

class SerializationError(OSError):
    """ Indicates an serialization error. """


SERIALIZERS = []
""" Known serializers that are used for dynamic serializer assignment. """


class Serializer:
    """ Base class for all serializers.

    Args:
        desc (str): Descriptions of the information that is handled.
    """

    WELL_KNOWN = []

    fmt = None
    """ Format descriptor of the serializer. """

    @classmethod
    def from_well_known(cls, fmt, desc):
        """ Get serializer from format string.

        Args:
            fmt (str): Format string to find serializer for.
            desc (str): Description of the handled data for the serializer.
        Returns:
            Serializer: Serializer that can handle the format.
        Raises:
            ValueError: If not matching serializer was found.
        """
        for ser_cls in cls.WELL_KNOWN:
            ser_fmt = ser_cls.fmt
            if "/" in ser_fmt:
                if fmt.startswith(ser_fmt.split("/")[0]):
                    return ser_cls.from_fmt(fmt, desc)
            elif ser_fmt == fmt:
                return ser_cls.from_fmt(fmt, desc)
        raise ValueError("Unknown serializer")

    def __init__(self, desc):
        if not isinstance(desc, str):
            raise ValueError(f"Description must be a string, was {desc}")
        self.desc = desc

    @property
    def desc_payload(self):
        """
        Returns:
            bytes: Description as bytes.
        """

        return self.desc.encode()

    @property
    def fmt_payload(self):
        """
        Returns:
            bytes: Format as bytes.
        """

        return self.fmt.encode()

    def __eq__(self, other):
        """
        Returns:
            bool: True if Serializers handle the same format, else False.
        """

        if not isinstance(other, Serializer):
            return False
        return self.fmt == other.fmt

    @classmethod
    def from_fmt(cls, fmt, desc):
        """ Instantiate serializer from format.

        Args:
            fmt (str): Format to create from.
            desc (str): Description of information to handle.
        Returns:
            Serializer: New serializer.
        Raises:
            ValueError: If the format is invalid.
        """

        if cls.fmt != fmt:
            raise ValueError("Invalid format")
        return cls(desc=desc)
