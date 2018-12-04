#!/usr/bin/python3
""" Helper script that configures a mauzr network.

Takes a YAML file that contains the network description and publishes
it in the config tree of the local MQTT broker.
"""

import logging
import threading
import time
import argparse
from pathlib import Path
import yaml
from mauzr.serializer.generic import Serializer, Bytes
from mauzr.shell import Shell

__author__ = "Alexander Sowitzki"

def whipe(shell, log):
    """ Whipe present cfg, fmt and desc trees.

    Args:
        shell (Shell): Shell to use.
        log (logging.Logger): Logger to use.
    """

    log.info("Begin whiping cfg tree")

    ser = Bytes(shell=shell, desc="None")
    handles = []

    def _whipe_cb(_value, handle):
        handles.append(handle)

    for branch in ("cfg", "fmt", "desc"):
        tokens = [shell.mqtt(topic=f"{branch}/#", ser=ser, qos=1,
                             retain=True).sub(_whipe_cb, wants_handle=True)]
        time.sleep(3)
        del tokens
        for h in handles:
            log.info("Whiping %s", h.topic)
            h(bytes())
        handles = []
    log.info("Done whiping cfg tree")

def process_topics(shell, log, topic_data):
    """ Publish meta of created topics.

    Args:
        shell (Shell): Shell to use.
        log (logging.Logger): Logger to use.
        topic_data (tuple): Tuple of the created topics.
    """

    log.info("Begin publishing topic metadata")
    for td in topic_data:
        ser = Serializer.from_well_known(shell=shell,
                                         fmt=td["fmt"], desc=td["desc"])
        handle = shell.mqtt(topic=td["topic"], qos=td["qos"],
                            retain=td["retain"], ser=ser)
        log.info("Publishing meta for %s", handle.topic)
        handle.publish_meta(configured=True)
    log.info("Done publishing topic metadata")

def process_cfg(shell, log, data, offset):
    """ Publish meta of created topics.

    Args:
        shell (Shell): Shell to use.
        log (logging.Logger): Logger to use.
        data (dict): Configuration of the current level.
        offset (list): Key path to this dict.
    Raises:
        ValueError: On error.
    """

    if not isinstance(data, dict):
        return

    special = frozenset(("_value",))
    keys = frozenset(data.keys())
    topic = "/".join(offset)

    if "_value" in keys:
        try:
            value, fmt, desc = data["_value"]
        except ValueError:
            raise ValueError(f"Invalid _value: {topic}")
        ser = Serializer.from_well_known(shell=shell, fmt=fmt, desc=desc)
        h = shell.mqtt(topic=topic, ser=ser, qos=1, retain=True)
        h.publish_meta(configured=True)
        h(value)
        log.info("%s -> %s", h.topic, value)
    elif not keys - special:
        raise ValueError(f"Topic contains no children or value: {topic}")

    for key in keys - special:
        process_cfg(shell, log, data[key], offset + [key])

def run(shell):
    """ Perform the actual work. """

    log = shell.log.getChild("Configurator")

    whipe(shell, log)

    try:
        for path in shell.args.paths:
            try:
                log.info("Handling path %s", path)
                data = yaml.load(open(path, "r"))
                process_topics(shell, log, data["topics"])
                process_cfg(shell, log, data["cfg"], ["cfg"])
            except OSError:
                log.exception("Path %s failed", path)
    finally:
        log.info("Shutting down")
        shell.shutdown()
        log.info("Done")

def main():
    """ Program entry point. """

    logging.basicConfig()

    parser = argparse.ArgumentParser("Configurator for mauzr networks")
    parser.add_argument("paths", nargs='+')
    shell = Shell(thin=True, parser=parser)

    t = threading.Thread(target=shell.run)
    t.start()
    run(shell)
    t.join()

if __name__ == "__main__":
    main()
