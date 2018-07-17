""" Image elements. """

import pygame
from mauzr.agents.gui import Element
from mauzr.serializer.gui import PygameSurface

__author__ = "Alexander Sowitzki"


class FeedDisplayer(Element):
    """ Show an image feed on the GUI window. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.input_topic("feed", r"image", "Feed image",
                         ser=PygameSurface("Feed display"))
        self.feed_surf, self.feed_rect = None, None

    def on_input(self, surface):
        self.feed_surf = pygame.transform.scale(surface, self.rect)
        self.feed_rect = self._image_surf.get_rect()

    def _draw_foreground(self):
        """ Draw the element. """

        if self.feed_surf:
            self.surface.blit(self.feed_surf, self.feed_rect)
