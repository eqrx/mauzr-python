""" Access GPIO via Sysfs. """

import struct
import time
import os
import mmap
import select
import io
import threading
from contextlib import contextmanager, suppress
from mauzr.agent import Agent

__author__ = "Alexander Sowitzki"


class Output(Agent):
    """ Connector for a general purpose output. """

    def __init__(self, *args, **kwargs):
        self.fd = None
        super().__init__(*args, **kwargs)
        self.option("identifier", "str", "Output name")
        self.input_topic("input", r"struct\/[?B]",
                         "Input topic for the pin value")
        self.update_agent(arm=True)

    def on_input(self, value):
        """ Write value to the GPO. """
        # Write to file
        self.fd.write(f"{1 if value else 0}\n")
        # Be sure to flush
        self.fd.flush()

    @contextmanager
    def setup(self):
        identifier = self.identifier
        # Export pin.
        open("/sys/class/gpio/export", "w").write("{}".format(identifier))
        # Set as output.
        with open(f"/sys/class/gpio/gpio{identifier}/direction", "w") as fdir:
            fdir.write("out")

        # Prepare value file descriptor and yield.
        with open(f"/sys/class/gpio/gpio{identifier}/value", "wt") as self.fd:
            yield
            self.fd = None

        # Clean up.
        with suppress(IOError):
            with open("/sys/class/gpio/unexport", "w") as unexport:
                unexport.write(f"{identifier}\n")


class Input(Agent):
    """ Connector for a general purpose input. """

    def __init__(self, *args, **kwargs):
        self.fd, self.value = None, None
        # Task to ensure an input has stabilized.
        self.stabilize_task = None
        super().__init__(*args, **kwargs)
        self.option("identifier", "str", "Input identifier")
        self.option("edge", "str", "Edge to detect")
        self.output_topic("output", r"struct\/[?B]",
                          "Output topic for the pin value")
        self.update_agent(arm=True)

    def on_stable(self):
        """ Called when the input value is considered stable - publishes it. """

        self.output(self.value)

    def select_inputs(self):
        """ Select the GPI until it has a new value. """

        while True:
            try:
                select.select([], [], [self.fd])
                if self.fd is None:
                    return
                # Rewind file.
                self.fd.seek(0, io.SEEK_SET)
                # Read and convert value.
                self.value = self.fd.read(1) == "1"
                # Since the value has changed (re-)start the stabilize task.
                self.stabilize_task.enable()
            except OSError:
                if self.fd is not None:
                    # Log exception into logger.
                    self.log.exception("Error with select")
                    # Restart agent on error.
                    self.update_agent(restart=True)

    @contextmanager
    def setup(self):
        self.stabilize_task = self.after(0.02, self.on_stable)
        identifier, edge = self.identifier, self.edge
        # Export pin.
        open("/sys/class/gpio/export", "w").write(f"{identifier}\n")
        # Set as input.
        with open(f"/sys/class/gpio/gpio{identifier}/direction", "w") as dirf:
            dirf.write("in")
        # Set edge we are interested in.
        open(f"/sys/class/gpio/gpio{identifier}/edge", "w").write(edge + "\n")
        # Open value file.
        with open(f"/sys/class/gpio/gpio{identifier}/value", "rt") as self.fd:
            # Dispatch a dedicated thread for selecting the value file.
            threading.Thread(target=self.select_inputs,
                             name=f"GPIO {identifier} select",
                             daemon=True).start()
            # Yield
            yield
            self.fd = None
        self.stabilize_task = None

        # Clean up.
        with suppress(IOError):
            with open("/sys/class/gpio/unexport", "w") as unexport:
                unexport.write(f"{identifier}\n")

class RaspberryInput(Input):
    """ Connector for a general purpose input on the raspberry pi.

    This agents supports setting the pull up/down resistors for the
    corresponding pin. This setting cannot be applied with the generic GPIO
    driver and must use gpiomem.
    """

    PULLUPDN_OFFSET = 37
    PULLUPDNCLK_OFFSET = 38

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.option("pull", "str", "Pull up/down setting")
        self.gpiomem = None

    @contextmanager
    def setup(self):
        identifier, pull = int(self.identifier), self.pull
        fd = os.open("/dev/gpiomem", os.O_RDWR | os.O_SYNC)
        with mmap.mmap(fd, 4*1024) as m:
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
            c_offset = (self.PULLUPDNCLK_OFFSET + identifier // 32) * 4
            c_loc = slice(c_offset, c_offset + 4)

            # Write value to set register
            m[v_loc] = struct.pack("<I", v)
            time.sleep(0.001)
            # Specify pin to apply
            m[c_loc] = struct.pack("<I", 1 << (identifier % 32))
            time.sleep(0.001)
            # Clear set register
            m[v_loc] = struct.pack("<I", v_clear)
            # Clear clocking register
            m[c_loc] = struct.pack("<I", 0)

        with super().setup():
            yield
