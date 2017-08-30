""" Vector helper module. """
__author__ = "Alexander Sowitzki"

class Vector:
    """ A vector of arbitrary length.

    :param args: List of values used to create the value set.
    :type args: list
    """

    def __init__(self, *args):
        self.values = tuple(args)

    def __getitem__(self, key):
        return self.values[key]

    def __add__(self, other):
        if isinstance(other, Vector):
            other = other.values
        return Vector(*[a+b for a, b in zip(self.values, other)])

    def __sub__(self, other):
        if isinstance(other, Vector):
            other = other.values
        return Vector(*[a-b for a, b in zip(self.values, other)])

    def __floordiv__(self, other):
        if isinstance(other, (int, float)):
            return Vector(*[a//other for a in self.values])
        elif isinstance(other, Vector):
            other = other.values
        return Vector(*[a//b for a, b in zip(self.values, other)])

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return Vector(*[a*other for a in self.values])
        return Vector(*[a*b for a, b in zip(self.values, other)])

    def __repr__(self):
        return f"mauzr.gui.vector.Vector(*{self.values})"
