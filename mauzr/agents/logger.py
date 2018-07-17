""" Sending logs to the message broker. """

import logging
import contextlib
from mauzr import Agent
from mauzr.serializer import JSON
from mauzr.mqtt import Handle

__author__ = "Alexander Sowitzki"


class _ShowerFilter(logging.Filter):
    """ Filters out log messages from MQTT and logger to prevent log shower.

    Args:
        shell (mauzr.shell.Shell): Shell to filter for.
    """

    def __init__(self, shell):
        super().__init__()

        # Create a blacklist of agents to ignore.
        self.blacklist = [".".join((shell.name, n)) for n in
                          ("mqtt", "logger")]

    def filter(self, rec):
        # Ignore if agent in blacklist of level is debug.
        return rec.levelno > logging.DEBUG or rec.name not in self.blacklist


class LogSender(logging.Handler, Agent):
    """ Send agent log output to message broker.

    WARNING: Do not use this while LogCollector is active.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Log at least info or more if specified.
        level = max(logging.INFO, self.shell.log.level)
        logging.Handler.__init__(self, level=level)

        # Prepare sending.
        self._ser = JSON("Log output")
        self._root_topic = Handle(self.shell.mqtt, self.shell.sched,
                                  topic="log", ser=None, qos=0, retain=True)

        # Attach to root logger.
        self.addFilter(_ShowerFilter(self.shell))
        self.core.log.addHandler(self)

    def emit(self, record):
        # Get handler
        h = self._root_topic.child(record.name.replace(".", "/"),
                                   ser=self._ser, qos=1, retain=False)
        # Convert message to JSON
        data = dict(record.__dict__)
        # Punch stack trace into message
        if data["exc_info"]:
            data["exc_info"] = [str(e) for e in data["exc_info"]]
        # Publish message and ignore failure
        with contextlib.suppress(OSError):
            h(data)

class LogCollector(Agent):
    """ Dump logs from the message broker into the local logger and to file.

    WARNING: Do not use this while LogSender is active.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Subscribe to all logs.
        self._ser = JSON("Log output")
        root_topic = Handle(self.shell.mqtt, self.shell.sched,
                            topic="log/#", ser=None, qos=0, retain=True)
        self.static_input(root_topic, self._on_log, sub={"wants_handle": True})

        # Setup logging to file.
        handler = logging.FileHandler(self.shell.args.data_path/"log")
        self.core.log.addHandler(handler)

    @staticmethod
    def _on_log(record, topic):
        log = logging.getLogger(".".join(topic.chunks[1:]))
        log.filter(log.makeRecord(**record))
