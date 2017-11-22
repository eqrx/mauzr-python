#!/usr/bin/python3
""" Functions helping to view images. """
__author__ = "Alexander Sowitzki"

import tkinter
import tkinter.ttk
import datetime
import PIL.ImageTk # pylint: disable=import-error
import PIL.ImageFont
import PIL.ImageDraw
import mauzr
from mauzr.util.image.serializer import ImageSerializer

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

    def __init__(self, core, tkroot, cfgbase="viewer", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._scale = cfg.get("scale", True)
        self._mode = cfg.get("mode", "r")
        self._topic = cfg["topic"]
        self._stamp = cfg.get("stamp", False)
        self._rotation = cfg.get("rotation", None)
        core.mqtt.subscribe(self._topic, self._on_image,
                            ImageSerializer(self._mode), 0)
        self.panel = tkinter.ttk.Label(tkroot)
        self.panel.pack(expand=True, fill="both")
        self.panel.after(1000//30, self._on_update)
        self._image = None
        self._freeze = False
        self._root = tkroot
        self._image_received = None
        self._font = PIL.ImageFont.load_default()
        tkroot.bind("<Key>", self._on_key)

    def _on_key(self, event):
        if event.char == "f":
            self._toggle_freeze()

    def _toggle_freeze(self):
        self._freeze = not self._freeze
        title = "Image viewer"
        if self._freeze:
            title += " - FREEZE"
        self._root.wm_title(title)

    def _on_update(self, e=None):
        if self._image and not self._freeze:
            tkimage = PIL.ImageTk.PhotoImage(self._image)
            self.panel.configure(image=tkimage)
            self.panel.image = tkimage
            self._image = None
        self.panel.after(1000//30, self._on_update)

    def _on_image(self, topic, image):
        if self._scale:
            maximum = (self.panel.winfo_width(), self.panel.winfo_height())
            target = image.size
            target = (int(target[0] * maximum[1]/target[1]),
                      int(target[1] * maximum[1]/target[1]))
            if target[0] > maximum[0]:
                target = (int(target[0] * maximum[0]/target[0]),
                          int(target[1] * maximum[0]/target[0]))
            image = image.resize(target, PIL.Image.ANTIALIAS)
        if self._rotation:
            image = image.rotate(self._rotation)
        if self._stamp:

            draw = PIL.ImageDraw.Draw(image)
            draw.text((0, 0),
                      str(datetime.datetime.now()),
                      (255, 255, 255), font=self._font)

        self._image = image

def main():
    """ Entry point for the image viewer. """

    root = tkinter.Tk()
    root.wm_title("Image viewer")
    root.geometry("800x480+0+0")

    core = mauzr.linux("mauzr", "imageviewer")
    core.setup_mqtt()
    Viewer(core, root)
    with core:
        root.mainloop()

if __name__ == "__main__":
    main()
