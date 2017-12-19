""" Simple audio driver for linux. """
__author__ = "Alexander Sowitzki"

import subprocess
import mauzr
import mauzr.serializer

class Driver:
    """ Simple audio driver for linux.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Required core units**:

        - mqtt

    **Configuration:**

        - **base** (:class:`str`) - Base for topics.

    **Input topics:**

        - **/say** (:class:`str`) - Say a given text.
        - **/play** (:class:`str`) - Play a file under the given path.
    """

    def __init__(self, core, cfgbase="audio", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        # Current process
        self._process = None

        core.mqtt.subscribe(cfg["base"] + "/say", self._on_say,
                            mauzr.serializer.String, 0)
        core.mqtt.subscribe(cfg["base"] + "/play", self._on_play,
                            mauzr.serializer.String, 0)

    def _process_done(self):
        # Return True when playback is done

        if self._process is None:
            # No process - Done
            return True
        else:
            # Poll process
            self._process.poll()
            if self._process.returncode is not None:
                # Process finished
                self._process = None
                return True

    def _on_say(self, _topic, text):
        # Ignore if already playing
        if self._process_done():
            e = subprocess.Popen(("espeak", "--stdout", text),
                                 stdout=subprocess.PIPE)
            self._process = subprocess.Popen(("aplay", "-t", "wav", "-"),
                                             stdin=e.stdout)
            e.stdout.close()

    def _on_play(self, _topic, path):
        # Ignore if already playing
        if self._process_done():
            self._process = subprocess.Popen(("aplay", path))

def main():
    """ Entry point for audio driver. """

    core = mauzr.linux("mauzr", "audio")
    core.setup_mqtt()
    Driver(core)
    core.run()

if __name__ == "__main__":
    main()
