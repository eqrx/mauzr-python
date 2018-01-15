""" Image elements. """

import pygame  # pylint: disable=import-error
from mauzr.gui import BaseElement

__author__ = "Alexander Sowitzki"


class FeedDisplayer(BaseElement):
    """ Display an image feed.

    :param core: Core instance.
    :type core: object
    :param input: Topic and QoS of input.
    :type input: tuple
    :param placement: Center and size of the element.
    :type placement: tuple
    """

    # pylint: disable = redefined-builtin
    def __init__(self, core, input, placement):
        from mauzr.util.image.serializer import Pygame as SurfaceSerializer
        core.mqtt.subscribe(input[0], self._on_image,
                            SurfaceSerializer, input[1])
        BaseElement.__init__(self, *placement)
        self._image_surface = None
        self._image_rect = None

    def _on_image(self, _topic, surface):
        self._image_surface = pygame.transform.scale(surface,
                                                     self._size.values)
        self._image_rect = self._image_surface.get_rect()

    def _draw_foreground(self):
        """ Draw the element. """

        if self._image_surface:
            self._surface.blit(self._image_surface, self._image_rect)
