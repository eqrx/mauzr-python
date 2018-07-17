""" Camera functions. """

from contextlib import contextmanager
import cv2  # pylint: disable=import-error
from mauzr import Agent, PollMixin

__author__ = "Alexander Sowitzki"


class CapturePublisher(Agent, PollMixin):
    """ Publishes camera captures. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.camera = None

        self.output_topic("output", r"image\/.*",
                          "Output topic for the camera image")
        self.option("resolution", "struct/!HH",
                    "Width and height of captured image")
        self.option("framerate", "struct/!H",
                    "Framerate of captured image")

    @contextmanager
    def setup(self):
        with cv2.VideoCapture(0) as self.camera:
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.camera.set(cv2.CAP_PROP_FPS, self.framerate)

    def poll(self):
        """ Poll camera image and publish it. """

        self.output(self.camera.read()[1])
