""" Camera functions. """

__author__ = "Alexander Sowitzki"

# pylint: disable = import-error
import cv2
import mauzr

class Driver:
    """ Capture camera frames and publish them to the network.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units:**

        - *mqtt*

    **Configuration:**

        - *base*: Base for topics (``str``).
        - *flip*: Tuple of bools if to do vflip or hflip.
        - *framerate*: Number of frames to capture per second (``int``).
        - *address*: I2C address of the device (``int``).
        - *framerate*: Normal output frequency in milliseconds (``int``).
        - *slowinterval*: Slow frequency in milliseconds (``int``).

    **Output topics:**

        - `base` + *live*: Camera frames captured with maximum speed as jpeg.
    """

    def __init__(self, core, cfgbase="camera", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._mqtt = core.mqtt
        self._image = None
        self._base = cfg["base"]
        self._camera = cv2.VideoCapture(0)

        resolution = cfg.get("resolution", None)
        if resolution:
            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

        framerate = cfg.get("framerate", None)
        if framerate:
            self._camera.set(cv2.CAP_PROP_FPS, framerate)

        vflip = cfg.get("vflip", False)
        hflip = cfg.get("hflip", False)

        self._flip = None
        if vflip and hflip:
            self._flip = -1
        elif hflip:
            self._flip = 0
        elif vflip:
            self._flip = 1

        core.mqtt.setup_publish(self._base + "live", None, 0)

        if "slowinterval" in cfg:
            core.mqtt.setup_publish(self._base + "slow", None, 0)
            core.scheduler(self._publish_slow, cfg["slowinterval"],
                           single=False).enable()


    def _publish_slow(self):
        image = self._image
        if image:
            self._image = None
            self._mqtt.publish(self._base + "slow", image, True)

    def __call__(self):
        # Capture and publish frames.

        while True:
            image = self._camera.read()[1]
            if self._flip is not None:
                image = cv2.flip(image, self._flip)
            image = cv2.imencode('.jpg', image)[1]
            self._image = image.tostring()
            self._mqtt.publish(self._base + "live", self._image, False)

def main():
    """ Entry point for camera feeder. """

    core = mauzr.cpython("mauzr", "camera")
    core.setup_mqtt()
    driver = Driver(core)

    with core:
        driver()

if __name__ == "__main__":
    main()
