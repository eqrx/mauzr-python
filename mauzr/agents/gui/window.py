""" GUI panels. """

import weakref
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
        self.__bell_task = None
        self.add_context(self.__bell_context)

    @contextmanager
    def __bell_context(self):
        self.__bell_task = self.every(60,
                                      self.maintain_bell).enable(instant=True)
        yield
        self.__bell_task = None

    def maintain_bell(self):
        """ Maintain bell function. """

        if False in [e.state_acknowledged for e in self.elements]:
            self.bell_sound.play()


class Window(BellMixin, Agent, PollMixin):
    """ A GUI window. """


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cell_dimensions, self.cell_draw_dimensions = None, None
        self.surf = None
        self.elements = weakref.WeakSet()
        self.rects = weakref.WeakKeyDictionary()

        self.option("dimensions", r"struct/!HH", "Window size in pixels")
        self.option("cells", r"struct/BB", "Window size in cells")
        self.option("title", "str", "Window title")

        self.update_agent(arm=True)

    def add_element(self, element):
        """ Add a GUI element.

        Args:
            element (mauzr.gui.Element): Element to add.
        """

        element.surface = None
        self.elements.add(element)

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

        self.shell.fire_agent_listeners("window")
        yield

    def poll(self):
        """ Perform the loop of pygame. """

        cd = self.cell_dimensions
        mbd = False
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                mbd = True
        mpos = pygame.mouse.get_pos()

        # Draw each tick
        for e in self.elements:
            if not e.active:
                continue
            pos, ext = e.positioning[0:2], e.positioning[2:4]
            rect = pygame.Rect([d*p+10 for d, p in zip(cd, pos)],
                               [d*e-20 for d, p, e in zip(cd, pos, ext)])
            surf = self.surf.subsurface(rect)
            if mbd and rect.collidepoint(mpos):
                e.on_click()
            e.draw(surf)
        pygame.display.flip()
