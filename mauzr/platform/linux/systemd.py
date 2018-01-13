""" Provide systemd functions """

import socket
import os

__author__ = "Alexander Sowitzki"


class Systemd:
    """ Systemd integration for agents.

    :param core: Core instance.
    :type core: object
    """

    def __init__(self, core):
        self._address = os.environ.get('NOTIFY_SOCKET', None)
        if self._address[0] == "@":
            self._address = '\0' + self._address[1:]
        self._socket = socket.socket(socket.AF_UNIX,
                                     socket.SOCK_DGRAM | socket.SOCK_CLOEXEC)
        self._watchdog_task = core.scheduler(self._watchdog, 5000,
                                             single=False)
        self._watchdog_task.enable(instant=True)
        self._start_task = core.scheduler(self._start, 0, single=True)
        self._core = core

    def __enter__(self):
        # Enable start task.

        self._start_task.enable()
        return self

    def __exit__(self, *exc_start):
        # Notify systemd about stop.

        self._notify("STOPPING=1\n")

    def _notify(self, message):
        # Pass message to systemd.

        self._socket.sendto(message.encode(), self._address)

    def _start(self):
        # Notify systemd about start.

        self._notify("READY=1\n")
        self._watchdog_task.enable(instant=True)

    def _watchdog(self):
        # Calm systemd watchdog and update status.

        status = "Connected" if self._core.mqtt.connected else "Disconnected"
        self._notify(f"WATCHDOG=1\nSTATUS={status}\n")
