#!/usr/bin/python3
""" Support for logging data to RRD databases. """
__author__ = "Alexander Sowitzki"

import pathlib
import time
import rrdtool # pylint: disable=import-error
import mauzr
from mauzr.platform.serializer import Struct

class RDDLogger:
    """ Log topics in RRD files.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units:**

        - mqtt

    **Configuration:**

        - **topics** (:class:`tuple`) - Topics to record.

          - **topic** (:class:`str`) - Input topic.
          - **qos** (:class:`int`) - Subscribe QoS.
          - **format** (:class:`str`) - Struct format of the topic.
          - **path** (:class:`str`) - Storage path for database.
          - **stepsize** (:class:`str`) - Time in seconds between logged values.
          - **timeout** (:class:`str`) - Time in seconds after topic is \
            considered timed out.
          - **valuerange** (:class:`tuple`) - Mininum and maxium values \
            to store.
          - **topic** (:class:`str`) - Input topic.
          - **average** (:class:`dict`) - Average records:

            - **minratio** (:class:`float`) - Minium ratio of known values \
              in range to form average.
            - **range** (:class:`int`) - Operation range in seconds.
            - **amount** (:class:`int`) - Amount of results to archive.

    **Input topics:**

        - `topics`: Topics configured to log.

    """

    DS_FORMAT = "DS:{}:GAUGE:{}:{}:{}"
    RRA_AVG_FORMAT = "RRA:AVERAGE:{}:{}:{}"

    def __init__(self, core, cfgbase="rrdlogger", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        mqtt = core.mqtt

        self._files = {}
        for cfgset in cfg["topics"]:
            topic = cfgset["topic"]
            path = pathlib.Path(cfgset["path"])
            self._files[topic] = path
            mqtt.subscribe(topic, self._on_message, Struct(cfgset["format"]), 0)
            if path.is_file():
                continue
            # pylint: disable=no-member
            path.parent.mkdir(parents=True, exist_ok=True)
            stepsize = cfgset["stepsize"]

            cmd = [path, "-O", "-s", stepsize,
                   self.DS_FORMAT.format("value", cfgset["timeout"],
                                         *cfgset["valuerange"])]
            for avgcfg in cfgset["average"]:
                steprange = avgcfg["range"] // stepsize
                cmd.append(self.RRA_AVG_FORMAT.format(avgcfg["minratio"],
                                                      steprange,
                                                      avgcfg["amount"]))
            rrdtool.create(*[str(part) for part in cmd])

    def _on_message(self, topic, value):
        rrdtool.update(str(self._files[topic]),
                       "{}:{}".format(int(time.time()), value))

def main():
    """ Entry point for the rrd logger. """

    core = mauzr.linux("mauzr", "rrdlogger")
    core.setup_mqtt()
    RDDLogger(core)
    core.run()

if __name__ == "__main__":
    main()
