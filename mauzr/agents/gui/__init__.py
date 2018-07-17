""" GUI core components. """

from contextlib import contextmanager
import pygame  # pylint: disable=import-error
from mauzr import Agent
from mauzr.serializer import Eval

__author__ = "Alexander Sowitzki"

class ColorInputMixin:
    """ Mixin for element to provide background coloring. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.option("color_decider", None, None, ser=Eval("Color decider"))
        self.input_topic("color_input", r".*", "Color input", cb=self.set_color)
        self.colors = None
        self.add_context(self.color_input_context)

    @contextmanager
    def color_input_context(self):
        """ Context for the color input. """

        self.set_color(None)
        yield

    def set_color(self, value):
        """ Set the color of the element.

        Args:
            value (object): Parameter for the color decider.
        """

        colors = self.color_decider(value)  # Request color decision.
        if colors != self._colors:  # If color is same no change is self.
            self.on_new_state()
            self.colors = colors  # Remember colors

    def draw_background(self):
        """ Draw the background layer. """

        self.surface.fill(self.current_color)

    @property
    def current_color(self):
        """ The current color of this element. """

        # Take first element as default
        i = 0
        if not self.state_acknowledged:
            # Cycle if not acknowledged
            t = pygame.time.get_ticks()
            i = t // self.COLOR_DISPLAY_DURATION % len(self._state)
        return self._state[i]


class ConfirmationMixin:
    """ Mixin for element to state confirmation. """

    def on_click(self):
        """ Called when the element is clicked. """

        self.state_acknowledged = True

    def on_new_state(self):
        """ Called when a new state comes up. """

        self.state_acknowledged = False


class TextInputMixin:
    """ Mixin for element to provide foreground labeling. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.option("text_decider", None, None, ser=Eval("Text decider"))
        self.input_topic("text_input", r".*", "Text input", cb=self.set_text)
        self.text_rect, self.text_surf = None, None
        self.add_context(self.text_input_context)

    @contextmanager
    def text_input_context(self):
        """ Context for the text input. """

        self.set_text(None)
        yield

    def set_text(self, value):
        """ Set the text of the element.

        Args:
            value (object): Parameter for the text decider.
        """

        text = self.text_decider(value)  # Generate text
        # Make text objects
        self.text_surf = self.font.render(text, 1, (0, 0, 0))
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)

    def draw_foreground(self):
        """ Draw the text layer. """

        self.surface.blit(self.text_surf, self.text_rect)


class OutputMixin:
    """ Mixin for element to provide output capability. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.option("output_decider", None, None, ser=Eval("Output decider"))
        self.input_topic("output_paramter", r".*", "Output parameter",
                         cb=self.set_output)
        self.output_topic("output_topic", r".*", "Controller output")

        self.add_context(self.controller_context)

    @contextmanager
    def controller_context(self):
        """ Context for the text input. """

        self.set_output(None)
        yield

    def set_output(self, value):
        """ Set the output of the element.

        Args:
            value (object): Parameter for the output decider.
        """

        self.output_value = self.output_decider(value)  # Generate text

    def on_click(self):
        """ Called when the element is clicked. """

        self.output(self.output_value)


class Element(Agent):
    """ A base element for the GUI. """

    COLOR_DISPLAY_DURATION = 200
    FONT = pygame.font.SysFont("Segoe Print", 16)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_acknowledged = True
        self.rect, self.surface = None, None
        self.option("window", "str", "Name of the window")
        self.option("positioning", r"struct\/!4H", "Cell location (row, column)"
                    " and extent (row, column)")

    @contextmanager
    def setup(self):
        win, pos = self.shell.window, self.positioning
        win.add_element(self)
        self.rect = pygame.Rect(win.layout(pos[0:2], pos[2:4]))
        self.surface = win.surf.subsurface(self.rect)
        yield
        self._window.rm_element(self)

    def draw(self):
        """ Draw all part of the elements. """

        if not self.active:
            return
        self.draw_background()
        self.draw_foreground()

    def on_new_state(self):
        """ Called when a new state comes up. """

    def on_mouse(self, position):
        """ Called when the mouse is moved.

        Args:
            position (tuple): New mouse position
        """

        if self.rect.collidepoint(position):
            self.on_click()

    def draw_background(self):
        """ Draw the background layer. """

    def draw_foreground(self):
        """ Draw the text layer. """

    def on_click(self):
        """ Called when the element is clicked. """
