""" Access GPIO via Sysfs. """

import struct
import time
import os
import mmap
import select
import io
import contextlib

__author__ = "Alexander Sowitzki"


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
        self._inputs = {}
        self._outputs = {}

        cfg = core.config[cfgbase]
        cfg.update(kwargs)
        if cfg.get("poll", False):
            core.scheduler(self._poll_inputs, 100, single=False).enable()
        else:
            core.scheduler(self._select_inputs, 100, single=False).enable()

        # Schedule to check for changes every 100 ms

        self.listeners = []
        core.add_context(self)

    def __enter__(self):
        # Start unit.

        return self

    def __exit__(self, *exc_details):
        # Stop unit and reset all pins.

        for pin in self._inputs.values() + self._outputs.values():
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
        self._inputs[name] = {"name": name, "file": value_file}

    def setup_output(self, name, pwm=False, initial=False):
        """ Set pin as output.

        :param name: Numer of the pin.
        :type name: int
        :param pwm: If value if PWM.
        :type pwm: bool
        :param initial: Initial value to set.
        :type initial: bool
        :raises NotImplementedError: If PWM is set (currently not implemented)
        """

        if pwm:
            raise NotImplementedError("PWM currently not implemented on linux")

        # Export pin
        open("/sys/class/gpio/export", "w").write("{}".format(name))
        # Set as output
        with open(f"/sys/class/gpio/gpio{name}/direction", "w") as direction:
            direction.write("out")
        value_file = open(f"/sys/class/gpio/gpio{name}/value", "wt")
        # Open value file
        self._outputs[name] = {"name": name, "file": value_file}
        self[name] = float(initial)

    def __getitem__(self, name):
        # Retrieve value of an input pin.

        pin = self._inputs[name]
        pin["file"].seek(0, io.SEEK_SET)
        return pin["file"].read(1) == "1"

    def __setitem__(self, name, value):
        # Set the value of an output pin.

        pin = self._outputs[name]
        # Format value
        output = "{}\n".format(1 if value else 0)
        # Write to file
        pin["file"].write(output)
        # Be sure to flush
        pin["file"].flush()

    def _poll_inputs(self):
        for pin in self._inputs:
            value = self[pin["name"]]
            if pin.get("old", None) != value:
                pin["old"] = value
                [listener(pin["name"], value) for listener in self.listeners]

    def _select_inputs(self):
        # Check inputs for changes and inform listeners.
        # Check every value file with select
        files = [(pin["file"], pin["name"]) for pin in self._inputs.values()]
        _, _, changed_files = select.select([], [], files, 0)
        # Check each changed file
        for changed_file in changed_files:
            name = files[changed_file]
            # Inform all listeners
            [listener(name, self[name]) for listener in self.listeners]


class RaspberryPins(Pins):
    """ Use GPIO pins on the raspberry.

    :param core: Core instance.
    :type core: mauzr.Core
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Additional configuration.
    :type kwargs: dict
    """

    PULLUPDN_OFFSET = 37
    PULLUPDNCLK_OFFSET = 38

    def __init__(self, core, cfgbase="gpio", **kwargs):
        Pins.__init__(self, core, cfgbase, **kwargs)
        self.gpiomem = None

    def __enter__(self):
        Pins.__enter__(self)

        fd = os.open("/dev/gpiomem", os.O_RDWR | os.O_SYNC)
        self.gpiomem = mmap.mmap(fd, 4*1024)

        return self

    def __exit__(self, *exc_details):
        Pins.__exit__(self, *exc_details)

        self.gpiomem.close()

    def _setup_pull(self, name, pull):
        m = self.gpiomem

        # Slice for set register
        v_loc = slice(self.PULLUPDN_OFFSET*4, self.PULLUPDN_OFFSET*4+4)
        # Get current setting and clear pull
        v_clear = struct.unpack("<I", m[v_loc])[0] & ~3
        v = v_clear

        # Modify pull
        if pull == "down":
            v |= 1
        elif pull == "up":
            v |= 2

        # Slice for clocking register
        c_offset = (self.PULLUPDNCLK_OFFSET + name//32) * 4
        c_loc = slice(c_offset, c_offset + 4)

        # Write value to set register
        m[v_loc] = struct.pack("<I", v)
        time.sleep(0.001)
        # Specify pin to apply
        m[c_loc] = struct.pack("<I", 1 << (name % 32))
        time.sleep(0.001)
        # Clear set register
        m[v_loc] = struct.pack("<I", v_clear)
        # Clear clocking register
        m[c_loc] = struct.pack("<I", 0)
