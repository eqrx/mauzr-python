""" Integration with systemd. """

import os
import subprocess
from contextlib import contextmanager
from socket import socket, AF_UNIX, SOCK_DGRAM, SOCK_CLOEXEC
from mauzr import Agent

__author__ = "Alexander Sowitzki"


class Notify(Agent):
    """ Interface to systemd.

    When the shell is started via systemd this agent can be used to create
    a systemd service with the type notify. The agent informs systemd about
    the successful start and handles the watchdog. The watchdog is triggered
    every 5 seconds. If the scheduler blocks for too long the service is
    restarted.
    """

    sock = socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC)
    """ Communication socket. """

    def __init__(self, *args, **kwargs):
        # Fetch communication socket address.
        addr = os.environ['NOTIFY_SOCKET']
        if addr[0] == "@":
            addr = '\0' + addr[1:]
        self.addr = addr
        self.task = None
        super().__init__(*args, **kwargs)

        self.log.debug("Setting up for systemd")

        self.add_context(self.setup)

        self.update_agent(arm=True)

    @contextmanager
    def setup(self):
        # Mark service as started and activate watchdog.
        self.send("READY=1\nWATCHDOG=1\nSTATUS=Running\n")
        self.task = self.every(5, self.reset_watchdog).enable(instant=True)

        yield

        self.task = None

        # Notify about stop.
        self.send("STOPPING=1\n")

    def update_status(self, status):
        """ update service status.

        Args:
            status (str): Status message to send. May not contain a newline.
        """

        self.send(f"STATUS={status}\n")

    def reset_watchdog(self):
        """ Reset the watchdog. """

        self.send("WATCHDOG=1\n")

    def send(self, message):
        """ Pass information to systemd.

        Args:
            message (str): Message to pass.
        """

        self.sock.sendto(message.encode(), self.addr)


class Service(Agent):
    """ Manage a Systemd service. """


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.input_topic("active", r"struct\/\?",
                         "If target service should be active")
        self.option("service", "str", "Name of the service to manage")

        self.add_context(self.setup)
        self.update_agent(arm=True)


    def on_input(self, requested):
        """ Set active state. """

        running = subprocess.call(["systemctl", "is-active", self.service]) == 0
        if running == requested:
            return

        subprocess.check_call(["sudo", "systemctl",
                               "start" if requested else "stop", self.service])
