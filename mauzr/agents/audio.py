""" Simple audio driver for linux. """

import subprocess
from contextlib import contextmanager
from mauzr import Agent

__author__ = "Alexander Sowitzki"


class Player(Agent):
    """ Play a file or use espeak for TTS on the local machine. """

    def __init__(self, *args, **kwargs):
        # Current process
        self.process = None
        super().__init__(*args, **kwargs)

        self.input_topic("say", r"str", "Text to speak")
        self.input_topic("say", r"str", "File to play")

        self.update_agent(arm=True)

    @contextmanager
    def setup(self):
        yield
        if self.process is not None:
            self.process.kill()
            self.process = None

    def process_done(self):
        """ Check if the audio process is done.

        Returns:
            bool: If it is done.
        """

        # Return True when playback is done
        if self.process is None:
            # No process - Done
            return True
        # Poll process
        self.process.poll()
        if self.process.returncode is not None:
            # Process finished
            self.process = None
            return True
        return False

    def on_say(self, text):
        """ Say a given text. """

        # Ignore if already playing
        if self.process_done():
            e = subprocess.Popen(("espeak", "--stdout", text),
                                 stdout=subprocess.PIPE)
            self.process = subprocess.Popen(("aplay", "-t", "wav", "-"),
                                            stdin=e.stdout)
            # We are not interested in espeaks output, aplay is.
            e.stdout.close()

    def on_play(self, path):
        """ Play a given file path. """

        # Ignore if already playing
        if self.process_done():
            self.process = subprocess.Popen(("aplay", path))
