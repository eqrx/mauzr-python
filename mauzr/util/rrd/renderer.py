#!/usr/bin/python3
""" Renderer for RRD databases. """
__author__ = "Alexander Sowitzki"

import time
import itertools
import rrdtool # pylint: disable=import-error
import mauzr

class Renderer:
    """ Render graphs from RRD files.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Configuration:**

        - **interval** (:class:`int`) - Rendering interval in milliseconds.
        - **graphs** (:class:`tuple`) - Graphs to render.
          - **path** (:class:`str`) - Storage path for database.
          - **title** (:class:`str`) - Graph title.
          - **vlabel** (:class:`str`) - Y axis label.
          - **length** (:class:`int`) - X axis length in seconds.
          - **limits** (:class:tuple`) - Tuple of upper and lower limit \
              as floats.
          - *size** (:class:`tuple`) - Tuple of width and height in pixels.

    **Input topics:**

        - `topics`: Topics configured to log.

    """

    def __init__(self, core, cfgbase="rrdrenderer", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)
        self._cfg = cfg["graphs"]
        self._graph_task = core.scheduler(self._on_graph, cfg["interval"],
                                          single=False).enable(instant=True)

    def _on_graph(self):
        for cfg in self._cfg:
            size = [str(s) for s in cfg["size"]]
            limits = [str(s) for s in cfg["limits"]]
            g = [cfg["path"], "--imgformat", "PNG",
                 "-w", size[0], "-h", size[1],
                 "--vertical-label", cfg["vlabel"], "-t", cfg["title"],
                 "-s", str(round(time.time()-cfg["length"])),
                 "-l", limits[0], "-u", limits[1]]
            color_iterator = itertools.cycle(("ff0000", "00ff00", "0000ff",
                                              "ff00ff", "ffff00", "00ffff"))

            for entry in cfg["lines"]:
                color = next(color_iterator)
                g.append(f"DEF:{entry['name']}={entry['path']}:value:AVERAGE")
                g.append(f"LINE2:{entry['name']}#{color}:{entry['name']}")

            rrdtool.graph(g)

def main():
    """ Entry point for the rrd renderer. """

    core = mauzr.linux("mauzr", "rrdrenderer")
    Renderer(core)
    core.run()

if __name__ == "__main__":
    main()
