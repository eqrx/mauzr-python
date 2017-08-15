""" Montoring and control GUI. """
__author__ = "Alexander Sowitzki"

import enum
import pygame # pylint: disable=import-error
from mauzr.gui.vector import Vector

class BaseElement:
    """ An visible element inside a GUI.

    :param location: Center of the element.
    :type location: mauzr.gui.Vector
    :param size: Size of the element.
    :type size: mauzr.gui.Vector
    """

    def __init__(self, location, size):
        self._location = location
        self._size = size
        screen = pygame.display.get_surface()
        self._rect = pygame.Rect(location.values, size.values)
        self._surface = screen.subsurface(self._rect)

    def _on_click(self):
        """ Called when the element is clicked. """


    def on_mouse(self, position):
        """ Called on mouse click.

        :param position: Location of the cursor when clicked.
        :type position: tuple
        """

        if self._rect.collidepoint(position):
            self._on_click()

    def _draw_text(self):
        """ Draw text of this element.

        Should be overridden by visible mixins.
        """

    def _draw_background(self):
        """ Draw background of this element.

        Should be overridden by visible mixins.
        """

    def _draw_foreground(self):
        """ Draw foreground of this element.

        Should be overridden by visible mixins.
        """

    @property
    def _color(self):
        """ Color of the element as tuple. """

        return (150, 0, 0)

    def draw(self):
        """ Draw the element. """

        self._draw_background()
        self._draw_foreground()
        self._draw_text()

class RectBackgroundMixin:
    """ An rectangle element inside a GUI. """

    def _draw_background(self):
        self._surface.fill(self._color)


class ColorState(enum.Enum):
    """ State of :class:`mauzr.gui.ColorStateMixin`.

    Each state has a tuple of colors indicating it.
    They will be cycled through.
    """

    UNKNOWN = ((150, 0, 0),)
    """ State is unknown. """
    ERROR = ((150, 0, 0), (255, 0, 0))
    """ State indicates system error. """
    WARNING = ((150, 150, 0), (255, 255, 0))
    """ State is undesired. """
    INFORMATION = ((0, 150, 0), (0, 255, 0))
    """ State is good. """

class ColorStateMixin:
    """ Mixin for :class:`mauzr.gui.Element`, adding a color change based
    on a configurable state.

    :param conditions: Dictionary mapping :class:`mauzr.gui.ColorState` to
    functions. The function receives one parameter and should return True
    if the value indicates the mapped state.
    :type conditions: dict
    """

    COLOR_DISPLAY_DURATION = 200
    """ Display duration of a single color in milliseconds. """

    def __init__(self, conditions):
        self._state_conditions = conditions
        self._state = ColorState.UNKNOWN
        self._state_acknowledged = True

    def _update_state(self, value):
        """ The conditions functions are called in order of the state
        appearance in the state enum. If a function returns True the mapped
        state is applied to this mixin.
        """

        for state in [s for s in ColorState if s in self._state_conditions]:
            if self._state_conditions[state](value) and state != self._state:
                self._state = state
                return

    @property
    def _color(self):
        # Take first element as default
        i = 0
        if not self._state_acknowledged:
            # Cycle if not acknowledged
            t = pygame.time.get_ticks()
            i = t // self.COLOR_DISPLAY_DURATION % len(self._state.value)
        return self._state.value[i]

class TextMixin:
    """ Mixin for :class:`mauzr.gui.Element`, adding a text label.

    :param text: Initial text to display.
    :type text: str
    :param size: size of the text.
    :type size: mauzr.gui.Vector
    :param font_name: Name of the font.
    :type font_name: str
    :param font_size: Size of the font
    :type font_size: int
    """

    def __init__(self, text, size, font_name="Segoe Print", font_size=16):
        self._font = pygame.font.SysFont(font_name, font_size)
        self._text_offset = size // 2
        self._current_text = None
        self._text_surf = None
        self._text_rect = None
        self._text = text

    @property
    def _text(self):
        """ Text to display. """

        return self._current_text

    @_text.setter
    def _text(self, text):
        """ Set text to display. """

        self._current_text = text
        self._text_surf = self._font.render(text, 1, (0, 0, 0))
        c = self._text_offset.values
        self._text_rect = self._text_surf.get_rect(center=c)

    def _draw_text(self):
        """ Inject text into element. """

        self._surface.blit(self._text_surf, self._text_rect)


def pygame_loop(core, elements, fps=10):
    """ Perform the loop of pygame.

    :param core: Core instance.
    :type core: object
    :param elements: Elements to display.
    :type elements: mauzr.gui.Element
    :param fps: Refresh rate of the screen.
    :type fps: float
    """

    while not core.shutdown_event.is_set():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Return on quit
                pygame.quit()
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Inform elements when mouse if clicked
                pos = pygame.mouse.get_pos()
                [indicator.on_mouse(pos) for indicator in elements]

        # Draw each tick
        [indicator.draw() for indicator in elements]

        pygame.display.flip()
        pygame.time.wait(1000//fps)

def table_layout(offset, row, column, cell_size):
    """ Calculate position of an element in a grid layout.

    :param offset: Offset of the first element from the display borders.
    :type offset: mauzr.gui.Vector
    :param row: Row of the element.
    :type row: int
    :param column: Column of the element.
    :type column: int
    :param cell_size: Size of a cell.
    :type cell_size: mauzr.gui.Vector
    :returns: Position (center) of the element.
    :rtype: mauzr.gui.Vector
    """

    return offset + Vector(cell_size[0] * column, cell_size[1] * row)
