""" GUI panels. """
__author__ = "Alexander Sowitzki"

import pygame
from mauzr.gui.vector import Vector
from mauzr.gui.elements import Indicator, AgentIndicator
from mauzr.gui.elements import ToggleController, SimpleController

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
            **pixels** (:class:`tuple`): Display width and size in pixels (int).
            **cells** (:class:`tuple`): Row and cell count (int).
        - **fps** (:class:`int`): Refresh rate per second.
        - **title** (:class:`str`): Title of the window.
    """

    def __init__(self, core, cfgbase="panel", **kwargs):
        #cell_size, draw_size, offset, fps=10):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        pygame.init()
        display_size = Vector(*cfg["size"]["pixels"])
        pygame.display.set_mode(display_size.values)
        pygame.display.set_caption(cfg["title"])
        self._cell_size = Vector(*(display_size//cfg["size"]["cells"]))
        self._draw_size = self._cell_size - [10, 10]

        self._bell_sound = pygame.mixer.Sound("alarm.wav")
        self._bell_reset_task = core.scheduler(self._bell_reset, 10000,
                                               single=True)
        self._bell_check_task = core.scheduler(self._bell_check, 3000,
                                               single=False).enable()

        self.elements = []
        self._core = core
        self._fps = cfg["fps"]

    def _bell_check(self):
        if False in [indicator.state_acknowledged
                     for indicator in self.elements]:
            self._bell_reset_task.enable()
            self._bell_check_task.disable()
            self._bell_sound.play()

    def _bell_reset(self):
        self._bell_reset_task.disable()
        self._bell_check_task.enable()

    def loop(self):
        """ Perform the loop of pygame. """

        while not self._core.shutdown_event.is_set():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # Return on quit
                    pygame.quit()
                    return
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Inform elements when mouse if clicked
                    pos = pygame.mouse.get_pos()
                    [indicator.on_mouse(pos) for indicator in self.elements]

            # Draw each tick
            [indicator.draw() for indicator in self.elements]

            pygame.display.flip()
            pygame.time.wait(1000//self._fps)

    def agent_indicator(self, position, topic):
        """ Create a new :class:`mauzr.gui.elements.AgentIndicator`.

        :param position: Cell postion of the elemnt (row, column as ints).
        :type position: tuple
        :param topic: Topic to monitor.
        :type topic: str
        :returns: The new element.
        :rtype: mauzr.gui.elements.AgentIndicator
        """

        cell_location = self.layout(position)
        element = AgentIndicator(self._core, topic,
                                 cell_location, self._draw_size)
        self.elements.append(element)
        return element

    def indicator(self, position, topic, ser, label, fmt, conditions, timeout):
        """ Create a new :class:`mauzr.gui.elements.Indicator`.

        :param position: Cell postion of the elemnt (row, column as ints).
        :type position: tuple
        :param topic: Topic to monitor.
        :type topic: str
        :param ser: Serializer for the topic.
        :type ser: object
        :param label: Label to prepend the value with. Is separated from \
                      it by ": ".
        :type label: str
        :param fmt: Format to use for displaying the topic value. Is expected \
                    to be in curly braces and with implicit position \
                    reference. Will be concatenated to the internal format.
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

        cell_location = self.layout(position)
        element = Indicator(self._core, topic, ser, label, fmt, conditions,
                            timeout, cell_location, self._draw_size)
        self.elements.append(element)
        return element

    def toggler(self, position, topic, label, qos, retain):
        """ Create a new :class:`mauzr.gui.elements.ToggleController`.

        :param position: Cell postion of the elemnt (row, column as ints).
        :type position: tuple
        :param topic: Topic to manage.
        :type topic: str
        :param qos: QoS to use for publish.
        :type qos: int
        :param retain: True if publish shall be retained.
        :type retain: bool
        :param label: Label to prepend the value with. Is separated from \
                     it by ": ".
        :type label: str
        :returns: The new element.
        :rtype: mauzr.gui.elements.ToggleController
        """

        cell_location = self.layout(position)
        element = ToggleController(self._core, topic, qos, retain, label,
                                   cell_location, self._draw_size)
        self.elements.append(element)
        return element

    def sender(self, position,
               send_topic, cond_topic, qos, retain, payload, label):
        """ Create a new :class:`mauzr.gui.elements.SimpleController`.

        :param position: Cell postion of the elemnt (row, column as ints).
        :type position: tuple
        :param send_topic: Topic to send on.
        :type send_topic: str
        :param cond_topic: Topic that has to be True to send.
        :type cond_topic: str
        :param qos: QoS to use for publish.
        :type qos: int
        :param retain: True if publish shall be retained.
        :type retain: bool
        :param payload: Payload to send.
        :type payload: bool
        :param label: Label to prepend the value with. Is separated from \
                     it by ": ".
        :type label: str
        :returns: The new element.
        :rtype: mauzr.gui.elements.ToggleController
        """

        cell_location = self.layout(position)
        element = SimpleController(self._core, send_topic, cond_topic, qos,
                                   retain, payload, label,
                                   cell_location, self._draw_size)
        self.elements.append(element)
        return element

    def layout(self, position):
        """ Assign pixel position to table position.

        :param position: Cell postion of the elemnt (row, column as ints).
        :type position: tuple
        :returns: Pixel position as vector.
        :rtype: mauzr.gui.vector.Vector
        """

        return Vector(self._cell_size[0] * position[1],
                      self._cell_size[1] * position[0])
