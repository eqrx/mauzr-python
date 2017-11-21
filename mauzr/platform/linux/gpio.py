""" Access GPIO via Sysfs. """
__author__ = "Alexander Sowitzki"

import select
import io
import contextlib

class Pins:
    """ Use GPIO pins.

    :param core: Core instance.
    :type core: mauzr.Core
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Additional configuration.
    :type kwargs: dict
    """

    EDGE_MAPPING = {"none": "none", "rising": "rising",
                    "falling": "falling", "both": "both"}

    def __init__(self, core, cfgbase="gpio", **kwargs):
        self.pins = {}

        cfg = core.config[cfgbase]
        cfg.update(kwargs)
        if cfg.get("poll", False):
            core.scheduler(self._poll_inputs, 100, single=False).enable()
        else:
            core.scheduler(self._select_inputs, 100, single=False).enable()

        # Schedule to check for changes every 100 ms

        self.listeners = []

    def __enter__(self):
        # Start unit.

        return self

    def __exit__(self, *exc_details):
        # Stop unit and reset all pins.

        for pin in self.pins.values():
            # Unexport pin
            with contextlib.suppress(IOError):
                with open("/sys/class/gpio/unexport", "w") as unexport:
                    unexport.write("{}\n".format(pin["name"]))
            pin["file"].close()

    @staticmethod
    def _setup_pull(_name, pull):
        if pull != "none":
            raise NotImplementedError("Generic GPIO does not support pull")

    def setup_input(self, name, edge, pull):
        """ Set pin as input.

        :param name: ID of the pin.
        :type name: str
        :param edge: Edges to inform listeners about. May be "none", "rising",
                     "falling" or "both".
        :type edge: str
        :param pull: Pull mode of the pin. May be "none", "up" or "down".
        :type pull: str
        """

        if pull is None:
            pull = "none"
        if edge is None:
            edge = "none"
        edge = self.EDGE_MAPPING[edge]

        self._setup_pull(name, pull)

        # Export pin
        open("/sys/class/gpio/export", "w").write(f"{name}\n")
        # Set edge
        open(f"/sys/class/gpio/gpio{name}/edge", "w").write(edge + "\n")
        # Set as input
        with open(f"/sys/class/gpio/gpio{name}/direction", "w") as direction:
            direction.write("in")
        # Open value file
        value_file = open(f"/sys/class/gpio/gpio{name}/value", "rt")
        self.pins[name] = {"name": name, "type": "in", "file": value_file}

    def setup_output(self, name):
        """ Set pin as output.

        :param name: Numer of the pin.
        :type name: int
        """

        # Export pin
        open("/sys/class/gpio/export", "w").write("{}".format(name))
        # Set as output
        with open(f"/sys/class/gpio/gpio{name}/direction", "w") as direction:
            direction.write("out")
        value_file = open(f"/sys/class/gpio/gpio{name}/value", "wt")
        # Open value file
        self.pins[name] = {"name": name, "type": "out", "file": value_file}

    def __getitem__(self, name):
        # Retrieve value of an input pin.

        pin = self.pins[name]
        if pin["type"] != "in":
            raise KeyError(f"Not an input: {name}")
        pin["file"].seek(0, io.SEEK_SET)
        return pin["file"].read(1) == "1"

    def __setitem__(self, name, value):
        # Set the value of an output pin.

        pin = self.pins[name]
        if pin["type"] != "out":
            raise KeyError(f"Not an output: {name}")
        # Format value
        output = "{}\n".format(1 if value else 0)
        # Write to file
        pin["file"].write(output)
        # Be sure to flush
        pin["file"].flush()

    def _poll_inputs(self):
        for pin in [pin for pin in self.pins.values() if pin["type"] == "in"]:
            value = self[pin["name"]]
            if pin.get("old", None) != value:
                pin["old"] = value
                [listener(pin["name"], value) for listener in self.listeners]

    def _select_inputs(self):
        # Check inputs for changes and inform listeners.
        # Check every value file with select
        special_files = [pin["file"] for pin in self.pins.values()
                         if pin["type"] == "in"]
        _, _, changed_files = select.select([], [], special_files, 0)
        # Check each changed file
        for changed_file in changed_files:
            pin = [pin for pin in self.pins.values()
                   if pin["file"] == changed_file][0]
            # Inform all listeners
            [listener(pin["name"], self[pin["name"]])
             for listener in self.listeners]
