""" GUI panels. """

import pygame  # pylint: disable=import-error
from mauzr.gui.base import Vector
from mauzr.gui.elements.meta import Muter, Acceptor
from mauzr.gui.elements.indicator import AgentIndicator, Indicator
from mauzr.gui.elements.controller import ToggleController, SimpleController

__author__ = "Alexander Sowitzki"


class Table:
    """ Provide MQTT support.

    :param core: Core instance.
    :type core: mauzr.core.Core
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Configuration (mqtt section):**

        - **size** (:class:`dict`): Size settings.
            **pixels** (:class:`tuple`): Display width and height \
                                         in pixels (int).
            **cells** (:class:`tuple`): Row and cell count (int).
        - **fps** (:class:`int`): Refresh rate per second.
        - **title** (:class:`str`): Title of the window.
    """

    def __init__(self, core, cfgbase="panel", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        pygame.init()
        display_size = Vector(*cfg["size"]["pixels"])
        pygame.display.set_mode(display_size.values)
        pygame.display.set_caption(cfg["title"])
        self._cell_count = Vector(*cfg["size"]["cells"])
        self._cell_size = display_size//self._cell_count
        self._draw_size = self._cell_size - [10, 10]
        self._bell_sound = pygame.mixer.Sound("/usr/share/sounds/alarm.wav")
        self._bell_reset_task = core.scheduler(self._bell_reset, 10000,
                                               single=True)
        self._bell_check_task = core.scheduler(self._bell_check, 3000,
                                               single=False).enable()

        self._core = core
        self._fps = cfg["fps"]
        self.elements = []

        e = Muter(self.layout(reversed(self._cell_count) - (1, 1)), self)
        self.elements.append(e)
        e = Acceptor(self.layout(reversed(self._cell_count) - (2, 1)), self)
        self.elements.append(e)

    def mute(self, value):
        """ Set mute of audio notifications.

        :param value: True if audio shall be muted.
        :type value: bool
        """

        if value:
            self._bell_reset_task.disable()
            self._bell_check_task.disable()
        else:
            self._bell_reset()

    def _bell_check(self):
        if False in [indicator.state_acknowledged
                     for indicator in self.elements]:
            self._bell_reset_task.enable()
            self._bell_check_task.disable()
            self._bell_sound.play()

    def _bell_reset(self):
        self._bell_reset_task.disable()
        self._bell_check_task.enable()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Return on quit
                pygame.quit()
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Inform elements when mouse if clicked
                pos = pygame.mouse.get_pos()
                [indicator.on_mouse(pos) for indicator in self.elements]

    def loop(self):
        """ Perform the loop of pygame. """

        while not self._core.shutdown_event.is_set():
            self._handle_events()

            # Draw each tick
            [indicator.draw() for indicator in self.elements]

            pygame.display.flip()
            pygame.time.wait(1000//self._fps)

    def agent_indicator(self, position, name):
        """ Create a new :class:`mauzr.gui.elements.AgentIndicator`.

        :param position: Cell postion of the elemnt (row, column as ints).
        :type position: tuple
        :param name: Agent to monitor.
        :type name: str
        :returns: The new element.
        :rtype: mauzr.gui.elements.AgentIndicator
        """

        element = AgentIndicator(self._core, name,
                                 self.layout(position, (1, 1)))
        self.elements.append(element)
        return element

    # pylint: disable = redefined-builtin
    def indicator(self, position, input, fmt, conditions, timeout):
        """ Create a new :class:`mauzr.gui.elements.Indicator`.

        :param position: Cell postion of the elemnt (row, column as ints).
        :type position: tuple
        :param input: Topic and QoS of input.
        :type input: tuple
        :param fmt: Format to use for displaying the topic value. Is expected \
                    to be in curly braces and with implicit position \
                    reference.
        :type fmt: str
        :param conditions: Dictionary mapping :class:`mauzr.gui.ColorState` \
                           to functions. The function receives one parameter \
                           and should return True if the value indicates \
                           the mapped state.
        :type conditions: dict
        :param timeout: If not None, an update of the topic is expected each \
                        ``timeout`` milliseconds. If a timeout occurs, \
                        the indicator is going into \
                        :class:`mauzr.gui.ColorState.ERROR`.
        :type timeout: int
        :returns: The new element.
        :rtype: mauzr.gui.elements.Indicator
        """

        element = Indicator(self._core, fmt, conditions, timeout,
                            input, self.layout(position, (1, 1)))
        self.elements.append(element)
        return element

    def toggler(self, position, label, retain, output):
        """ Create a new :class:`mauzr.gui.elements.ToggleController`.

        :param position: Cell postion of the elemnt (row, column as ints).
        :type position: tuple
        :param label: Label to prepend the value with. Is separated from \
                     it by ": ".
        :type label: str
        :param retain: True if publish shall be retained.
        :type retain: bool
        :param output: Topic and QoS of output.
        :type output: tuple
        :returns: The new element.
        :rtype: mauzr.gui.elements.ToggleController
        """

        element = ToggleController(self._core, label, retain, output,
                                   self.layout(position, (1, 1)))
        self.elements.append(element)
        return element

    def sender(self, position, cond_topic, label, output):
        """ Create a new :class:`mauzr.gui.elements.SimpleController`.

        :param position: Cell postion of the elemnt (row, column as ints).
        :type position: tuple
        :param cond_topic: Topic that has to be True to send.
        :type cond_topic: str
        :param label: Label to prepend the value with. Is separated from \
                     it by ": ".
        :param output: Topic, payload, QoS and retainment of the sender.
        :type output: str
        :type label: str
        :returns: The new element.
        :rtype: mauzr.gui.elements.ToggleController
        """

        element = SimpleController(self._core, cond_topic, label, output,
                                   self.layout(position, (1, 1)))
        self.elements.append(element)
        return element

    def layout(self, position, extend=(1, 1)):
        """ Assign pixel position to table position.

        :param position: Cell postion of the elemnt (row, column as ints).
        :type position: tuple
        :param extend: Amount of cells to fill.
        :type extend: Vector
        :returns: Pixel offset and draw size as as vectors.
        :rtype: tuple
        """

        offset = self._cell_size * reversed(position)
        size = self._draw_size * reversed(extend)

        return offset, size
