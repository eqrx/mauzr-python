""" Camera functions for raspberry. """
__author__ = "Alexander Sowitzki"

import time
import io
import picamera # pylint: disable=import-error
import mauzr

class Driver:
    """ Capture camera frames on raspberry and publish them to the network.

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
        - `base` + *0.1fps*: Camera frames captured with 0.1 fps as jpeg.
    """

    def __init__(self, core, cfgbase="camera", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._camera = picamera.PiCamera()
        self._camera.resolution = (1024, 768)
        self._camera.vflip = cfg["flip"][0]
        self._camera.hflip = cfg["flip"][1]
        self._camera.framerate = cfg["framerate"]
        self._mqtt = core.mqtt
        self._base = cfg["base"]
        core.mqtt.setup_publish(self._base + "live", None, 0)
        core.mqtt.setup_publish(self._base + "slow", None, 0)

        core.scheduler(self._publish_slow, cfg["slowinterval"],
                       single=False).enable()
        self._image = None

    def _publish_slow(self):
        image = self._image
        if image:
            self._image = None
            self._mqtt.publish(self._base + "slow", image, False)

    def __call__(self):
        # Capture and publish frames.

        while True:
            try:
                self._camera.start_preview()
                time.sleep(2)
                while True:
                    with io.BytesIO() as stream:
                        self._camera.capture(stream, 'jpeg')
                        stream.seek(0)
                        data = stream.read()
                        self._image = data
                        self._mqtt.publish(self._base + "live", data, False)
            except picamera.exc.PiCameraRuntimeError as err:
                print(err)
                time.sleep(3)
            finally:
                self._camera.stop_preview()

def main():
    """ Entry point for camera feeder. """

    core = mauzr.raspberry("mauzr", "camera")
    core.setup_mqtt()
    driver = Driver(core)

    with core:
        driver()

if __name__ == "__main__":
    main()
