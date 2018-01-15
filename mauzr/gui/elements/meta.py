""" Meta elements. """

from mauzr.gui import TextMixin, ColorStateMixin, RectBackgroundMixin
from mauzr.gui import BaseElement, ColorState

__author__ = "Alexander Sowitzki"


class Acceptor(TextMixin, RectBackgroundMixin, BaseElement):
    """ Acknowledge all states via one click.

    :param placement: Center and size of the element.
    :type placement: tuple
    :param panel: Panel to control.
    :type panel: mauzr.gui.panel.Table
    """

    def __init__(self, placement, panel):
        BaseElement.__init__(self, *placement)
        RectBackgroundMixin.__init__(self)
        TextMixin.__init__(self, "Clear")
        self._panel = panel

    def _on_click(self):
        # Assume click means acknowledge
        for element in self._panel.elements:
            element.state_acknowledged = True

    @property
    def _color(self):
        """ Color of the element as tuple. """

        return ColorState.INFORMATION.value[0]


class Muter(ColorStateMixin, TextMixin, RectBackgroundMixin, BaseElement):
    """ Mute audio notifications.

    :param placement: Center and size of the element.
    :type placement: tuple
    :param panel: Panel to control.
    :type panel: mauzr.gui.panel.Table
    """

    def __init__(self, placement, panel):
        BaseElement.__init__(self, *placement)
        RectBackgroundMixin.__init__(self)
        TextMixin.__init__(self, "Mute")
        conditions = {ColorState.WARNING: lambda v: v,
                      ColorState.INFORMATION: lambda v: not v}
        ColorStateMixin.__init__(self, conditions)
        self._muted = False
        self._panel = panel

    def _on_click(self):
        # Assume click means acknowledge
        self._muted = not self._muted
        self._update_state(self._muted)
        self._panel.mute(self._muted)

    @property
    def _color(self):
        """ Color of the element as tuple. """

        if self._muted:
            return ColorState.WARNING.value[0]
        return ColorState.INFORMATION.value[0]
