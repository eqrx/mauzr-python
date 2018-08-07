""" Image processing. """

import datetime
import cv2
from mauzr import Agent

__author__ = "Alexander Sowitzki"

ROTATION_MAP = {0: None, 90: cv2.ROTATE_90_CLOCKWISE,
                180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}


class Processor(Agent):
    """ Perform image operations on an input and republish the result. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.option("resize", "struct/!H", "Resize to resolution")
        self.option("timestamp", "struct/?", "Apply timestamp")
        self.option("rotate", "struct/!H", "Rotation in degrees")
        self.input_topic("input", r"image/.*", "Input image")
        self.output_topic("output", r"image/.*", "Input image")
        self.update_agent(arm=True)

    def on_input(self, image):
        """ Convert image. """

        if self.rotate in ROTATION_MAP:
            flip = ROTATION_MAP[self.rotate]
            image = cv2.rotate(image, flip)
        if self.resize:
            image = cv2.resize(image, self.resize)
        if self.timestamp:
            text = str(datetime.datetime.now())
            cv2.putText(image, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                        (255, 0, 0), 3, cv2.LINE_AA)
        self.output(image)
