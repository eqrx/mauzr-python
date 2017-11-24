""" Image processing. """

import mauzr
import mauzr.util.image.operation
from mauzr.util.image.serializer import OpenCV as ImageSerializer

class Processor:
    """ Process images. """

    def __init__(self, core, cfgbase="imageprocessor", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)
        self._mqtt = core.mqtt
        self._cfg = cfg

        self._ops = mauzr.util.image.operation.load_all(**cfg)
        self._last_image = None

        reduced = cfg.get("reduced", None)
        if reduced:
            core.mqtt.setup_publish(reduced["topic"], ImageSerializer, 0)
            core.scheduler(self._publish_reduced,
                           reduced["interval"], False).enable()

        core.mqtt.subscribe(cfg["in"], self._on_image, ImageSerializer, 0)
        core.mqtt.setup_publish(cfg["out"], ImageSerializer, 0)

    def _publish_reduced(self):
        image = self._last_image
        if image is not None:
            self._last_image = None
            self._mqtt.publish(self._cfg["reduced"]["topic"], image, True)

    def _on_image(self, _topic, image):
        for op in self._ops:
            image = op(image)
        self._last_image = image
        self._mqtt.publish(self._cfg["out"], image, True)

def main():
    """ Entry point for the image processor. """

    core = mauzr.cpython("mauzr", "imageprocessor")
    core.setup_mqtt()
    Processor(core)
    core.run()

if __name__ == "__main__":
    main()
