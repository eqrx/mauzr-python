""" GUI panels. """

import math
from contextlib import contextmanager
import pygame  # pylint: disable=import-error
from mauzr.agent.mixin.poll import PollMixin
from mauzr import Agent

__author__ = "Alexander Sowitzki"


class Point(tuple):
    """ A point in 3D space. """

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

        Args:
            x (float): Rotation around x axis in degree.
            y (float): Rotation around y axis in degree.
            z (float): Rotation around z axis in degree.
        Returns:
            Point: Rotated point.
        """

        v = self._rotate(self, 1, 2, x)
        v = self._rotate(v, 2, 0, y)
        return Point(*self._rotate(v, 0, 1, z))

    def project(self, w, fov, distance):
        """ Project point into 2D space.

        Args:
            w (tuple): Tuple containing width and height of the viewing window.
            fov (float): Field of view.
            distance (float): Camera distance.
        Returns:
            tuple: Tuple containing x and y coordinates.
        """

        f = fov / (distance + self[2])
        return (int(self[0] * f + w[0] / 2), int(-self[1] * f + w[1] / 2))


class BellMixin:
    """ Mixin for window for providing bell functions. """


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        pygame.init()

        self.bell_sound = pygame.mixer.Sound("/usr/share/sounds/alarm.wav")
        self.bell_reset_task = self.after(10, self.bell_mute, [False])
        self.bell_maintain_task = self.every(3, self.maintain_bell).enable()
        self.add_context(self.__bell_context)

    @contextmanager
    def __bell_context(self):
        yield

        self.bell_mute(True)

    def bell_mute(self, value):
        """ Mute or unmute bell.

        Args:
            value (bool): Mute if True else False
        """

        if value:
            self.bell_reset_task.disable()
            self.bell_maintain_task.disable()
        else:
            self.bell_reset_task.disable()
            self.bell_maintain_task.enable()

    def maintain_bell(self):
        """ Maintain bell function. """

        if False in [i.state_acknowledged for i in self.elements]:
            self.bell_mute(False)
            self.bell_sound.play()


class Window(BellMixin, Agent, PollMixin):
    """ A GUI window. """


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cell_dimensions, self.cell_draw_dimensions = None, None
        self.surf = None
        self.elements = set()

        self.option("dimensions", r"struct/!HH", "Window size in pixels")
        self.option("cells", r"struct/BB", "Window size in cells")
        self.option("title", "str", "Window title")

    @contextmanager
    def setup(self):
        assert self.is_ready()
        # Setup pygame.
        pygame.init()
        pygame.display.set_caption(self.title)
        self.surf = pygame.display.set_mode(self.dimensions)

        # Prepare fields.
        self.cell_dimensions = [a // b for a, b
                                in zip(self.dimensions, self.cells)]

        yield

    def layout(self, position, extent):
        """ Layout an element

        Args:
            position (Vector): Offset position in cells.
            extent (Vector): Extent in cells.
        Returns:
            tuple: Two vectors containing start and end position in pixels.
        """

        cd = self.cell_dimensions

        return  pygame.Rect([d*p+10 for d, p in zip(cd, position)],
                            [d*(p+e)-20 for d, p, e
                             in zip(cd, position, extent)])

    def add_element(self, element):
        """ Add a GUI element.

        Args:
            element (mauzr.gui.Element): Element to add.
        """

        self.elements.add(element)

    def rm_element(self, element):
        """ Add a GUI element.

        Args:
            element (mauzr.gui.Element): Element to add.
        """

        self.elements.discard(element)

    def handle_events(self):
        """ Handle pygame events. """

        # Parse all events.
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Inform elements when mouse if clicked
                pos = pygame.mouse.get_pos()
                [i.on_mouse(pos) for i in self.elements]

    def poll(self):
        """ Perform the loop of pygame. """

        self.handle_events()

        # Draw each tick
        [i.draw() for i in self.elements]
        pygame.display.flip()
