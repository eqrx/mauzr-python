""" GUI core components. """

from contextlib import contextmanager
import pygame  # pylint: disable=import-error
from mauzr import Agent
from mauzr.agent import AgentEvent as AE
from mauzr.serializer import Eval

__author__ = "Alexander Sowitzki"

class ColorInputMixin:
    """ Mixin for element to provide background coloring. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.option("color_decider", None, None,
                    ser=Eval(shell=self.shell, desc="Color decider"))
        self.input_topic("color_parameter", r".*", "Color input",
                         cb=self.set_color)
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
        if colors != self.colors:  # If color is same no change is self.
            self.on_new_state()
            self.colors = colors  # Remember colors

    def draw_background(self):
        """ Draw the background layer. """

        self.surface.fill(self.current_color())

    def current_color(self):
        """ The current color of this element. """

        # Take first element as default
        i = 0
        if not self.state_acknowledged:
            # Cycle if not acknowledged
            t = pygame.time.get_ticks()
            i = t // self.COLOR_DISPLAY_DURATION % len(self.state)
        return self.colors[i]


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
        self.option("text_decider", None, None,
                    ser=Eval(shell=self.shell, desc="Text decider"))
        self.input_topic("text_parameter", r".*", "Text input",
                         cb=self.set_text)
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
        self.option("output_decider", None, None,
                    ser=Eval(shell=self.shell, desc="Output decider"))
        self.input_topic("output_parameter", r".*", "Output parameter",
                         cb=self.set_output)
        self.output_topic("output", r".*", "Controller output")

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

        self.log.debug("Received output parameter: %s", value)

        self.output_value = self.output_decider(value)  # Generate text

    def on_click(self):
        """ Called when the element is clicked. """

        self.log.info("Setting output: %s", self.output_value)

        self.output(self.output_value)


class Element(Agent):
    """ A base element for the GUI. """

    COLOR_DISPLAY_DURATION = 200

    def __init__(self, *args, **kwargs):
        self.state_acknowledged = True
        self.rect, self.surface, self.font = None, None, None
        self.window = None
        self.window_ready = False
        super().__init__(*args, **kwargs)
        self.option("positioning", r"struct/!4H", "Cell location (row, column)"
                    " and extent (row, column)")
        self.shell.add_agent_listener(self.on_agent_changed)

    def on_agent_changed(self, agent, _event):
        """ Listener for agent events.

        Args:
            agent (mauzr.Agent): Agent that changed.
            _event (AE): Change type.
        """

        if agent.name != "window":
            return
        self.window = agent
        self.window_ready = agent.is_ready()
        req = AE.WANTS_ACTIVATION if self.is_ready() else AE.WANTS_DEACTIVATION
        self.shell.agent_changed(self, req)

    def is_ready(self):
        return super().is_ready() and self.window_ready

    @contextmanager
    def setup(self):
        assert self.window is not None
        pygame.init()
        self.font = pygame.font.SysFont("Segoe Print", 16)
        win, pos = self.window, self.positioning
        win.add_element(self)
        self.rect = win.layout(pos[0:2], pos[2:4])
        assert 0 not in pos[2:4]

        self.surface = win.surf.subsurface(self.rect)
        yield
        self.window.rm_element(self)

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
