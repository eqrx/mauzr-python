#!/usr/bin/python3
""" Helper script that configures a mauzr network.

Takes a YAML file that contains the network description and publishes
it in the config tree of the local MQTT broker.
"""

# TODO: Publish format for intermediate topics..

import struct
import logging
import argparse
import pathlib
import json
import yaml
from mauzr.shell import Shell

def struct_factory(loader, suffix, node):
    """ Pack struct data into bytes. """
    return struct.pack(suffix, loader.construct_sequence(node))

def json_factory(loader, node):
    """ Pack JSON data into bytes. """
    return json.dumps(loader.construct_mapping(node))

def topic_list_factory(loader, node):
    """ Pack topic data into bytes. """
    topics = [loader.construct_mapping(sn) for sn in node.value]
    return json.dumps(topics)

class Configurator:
    """ Configurator main class.

    Args:
        shell (mauzr.shell.Shell): Shell to use.
    """

    def __init__(self, shell):
        # Get required data from shell.
        self._core = shell
        self._mqtt = shell.mqtt
        self._path = shell.args.path

        # Add listener for MQTT connection.
        self._mqtt.connection_listeners.append(self._on_connection)
        # Create task for configuration.
        self._cfg_task = shell.sched.after(0, self._run)

    def _on_connection(self, status):
        # Start configuration task on first connection.
        if status and not self._cfg_task:
            self._cfg_task.enable()

    def _publish(self, topic, payload):
        # Get handle for topic.
        h = self._mqtt(topic="/".join(topic), qos=0, retain=True, ser=None)
        if isinstance(payload, str):
            # Convert string to bytes.
            payload = payload.encode()
        # Let handle publish payload.
        h(payload)
        h.publish_meta()

    def _walk_tree(self, path, entry):
        if "CONTENT" in entry:
            self._publish(path, entry["CONTENT"])
            del entry["CONTENT"]
        for key, value in entry.items():
            sub_path = path + [key]
            if isinstance(value, (bytes, str)):
                self._publish(sub_path, value)
            else:
                self._walk_tree(sub_path, value)

    def _run(self):
        config = yaml.load(self._path.open("r"))  # Load config.
        self._walk_tree(["cfg"], config["cfg"])  # Walk through config.
        self._core.sched.shutdown()  # Shut down core.

def main():
    """ Main method of configurator. """

    # Add factories
    yaml.add_multi_constructor("!struct/", struct_factory)
    yaml.add_constructor("!topic", json_factory)
    yaml.add_constructor("!topics", topic_list_factory)
    yaml.add_constructor("!json", json_factory)

    logging.basicConfig()  # Setup logging.
    # Setup argument parser.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=pathlib.Path,
                        description="Path to the network description file")
    shell = Shell(thin=True, parser=parser)  # Create thin shell.
    Configurator(shell)  # Create configurator.
    shell.run()  # Run shell.

if __name__ == "__main__":
    main()
