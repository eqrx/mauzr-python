""" Vector helper module. """
__author__ = "Alexander Sowitzki"

import math

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

    def __reversed__(self):
        return Vector(*reversed(self.values))

class Point:
    """ 3D Point.

    :param args: List of values used to create the value set.
    :type args: list
    """

    def __init__(self, *args):
        self.values = [float(a) for a in args]

    @staticmethod
    def _rotate(o, i, j, angle):
        radians = angle * math.pi / 180
        cos, sin = math.cos(radians), math.sin(radians)

        v = list(o)
        v[i] = o[i] * cos - o[j] * sin
        v[j] = o[i] * sin + o[j] * cos
        return v

    def rotated(self, x, y, z):
        """ Return rotated version of this point.

        :param x: Rotation around x axis in degree.
        :type x: float
        :param y: Rotation around y axis in degree.
        :type y: float
        :param z: Rotation around z axis in degree.
        :type z: float
        :return: Rotated point.
        :rtype: Point
        """

        v = self._rotate(self.values, 1, 2, x)
        v = self._rotate(v, 2, 0, y)
        return Point(*self._rotate(v, 0, 1, z))

    def project(self, w, fov, distance):
        """ Project point into 2D space.

        :param w: Tuple containing width and height of the viewing window.
        :type w: tuple
        :param fov: Field of view.
        :type fov: float
        :param distance: Camera distance.
        :type distance: float
        :returns: Tuple containing x and y coordinates.
        :rtype: tuple
        """

        v = self.values
        f = fov / (distance + v[2])
        return (int(v[0] * f + w[0] / 2), int(-v[1] * f + w[1] / 2))
