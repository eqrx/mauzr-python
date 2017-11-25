#!/usr/bin/python3
""" Functions helping to view images. """
__author__ = "Alexander Sowitzki"

import tkinter
import tkinter.ttk
import PIL.ImageTk # pylint: disable=import-error
import PIL.ImageFont # pylint: disable=import-error
import PIL.ImageDraw # pylint: disable=import-error
import cv2 # pylint: disable=import-error
import mauzr
import mauzr.util.image.operation
from mauzr.util.image.operation import resize
from mauzr.util.image.serializer import OpenCV as ImageSerializer

class Viewer:
    """ Display an image stream via GUI.

    :param core: Core instance.
    :type core: object
    :param tkroot: GUI root.
    :type tkroot: tkinter.Tk
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units:**

        - mqtt

    **Configuration:**

        - **topic** (:class:`str`) - Input topic.
        - **scale** (:class:`float`) - Scaling factor applied to the image
          before displaying.
        - **mode** (:class:`str`) - Image format. See :class:`PIL.Image.Image`.

    **Input topics:**

        - `topic`: Topic to receive images by (mode set by `mode`).
    """

    def __init__(self, core, tkroot, cfgbase="imageviewer", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._root = tkroot
        self._last_image = None
        self._freeze = False
        self._image_received = None
        self._last_image_size = None
        self._target_size = None
        self._panel_size = None

        self._scale = cfg.get("scale", True)
        self._topic = cfg["topic"]
        self._ops = mauzr.util.image.operation.load_all(**cfg)
        self._resizer = None

        core.mqtt.subscribe(self._topic, self._on_image,
                            ImageSerializer, 0)

        self.panel = tkinter.ttk.Label(tkroot)
        self.panel.pack(expand=True, fill="both")
        self.panel.after(1000//30, self._on_redraw)
        tkroot.bind("<Key>", self._on_key)
        tkroot.bind("<Configure>", self._on_window_resize)

    def _set_resizer(self):
        if self._last_image_size is None:
            return

        maximum = (self.panel.winfo_width(), self.panel.winfo_height())
        target = self._last_image_size
        target = (int(target[0] * maximum[1]/target[1]),
                  int(target[1] * maximum[1]/target[1]))
        if target[0] > maximum[0]:
            target = (int(target[0] * maximum[0]/target[0]),
                      int(target[1] * maximum[0]/target[0]))
        self._resizer = resize(resize=target)

    def _on_key(self, event):
        if event.char == "f":
            self._toggle_freeze()

    def _on_window_resize(self, event):
        self._panel_size = (self.panel.winfo_width(), self.panel.winfo_height())
        self._set_resizer()

    def _toggle_freeze(self):
        self._freeze = not self._freeze
        title = "Image viewer"
        if self._freeze:
            title += " - FREEZE"
        self._root.wm_title(title)

    def _on_redraw(self, e=None):
        if self._last_image is not None and not self._freeze:
            image = cv2.cvtColor(self._last_image, cv2.COLOR_BGR2RGB)
            image = PIL.Image.fromarray(image)
            tkimage = PIL.ImageTk.PhotoImage(image)
            self.panel.configure(image=tkimage)
            self.panel.image = tkimage
            self._last_image = None
        self.panel.after(1000//30, self._on_redraw)

    def _on_image(self, topic, image):
        for op in self._ops:
            image = op(image)
        shape = image.shape[0:2]
        if shape != self._last_image_size:
            self._last_image_size = shape
            self._set_resizer()
        self._last_image = self._resizer(image)
        #self._last_image = image

def main():
    """ Entry point for the image viewer. """

    root = tkinter.Tk()
    root.wm_title("Image viewer")
    root.geometry("800x480+0+0")

    core = mauzr.cpython("mauzr", "imageviewer")
    core.setup_mqtt()
    Viewer(core, root)
    with core:
        root.mainloop()

if __name__ == "__main__":
    main()
