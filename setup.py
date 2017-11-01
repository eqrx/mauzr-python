#!/usr/bin/python3
"""
.. module:: setup
   :platform: posix
   :synopsis: Build the mauzr package.

.. moduleauthor:: Alexander Sowitzki <dev@eqrx.net>
"""

import os
import re
import subprocess
import shutil
from pathlib import Path
import setuptools

class VersionInfo:
    """ Represent the current software version. """

    TAG_PATTERN = re.compile(r"v(\d\d(?:0\d|1[0-2])(?:[0-2]\d|3[0-1])\.\d\d?)")
    """ Pattern to match a version tag name. """

    def __init__(self):
        from subprocess import check_output
        # Fetch git refs
        log_output = check_output(("git", "log", "--simplify-by-decoration",
                                   "--decorate", "--pretty=%d", "HEAD")
                                 ).decode()
        # Find tags in refs
        match = VersionInfo.TAG_PATTERN.search(log_output)
        # Take last tag name and use match to define version
        tag_name = match.group(0)
        self.version = match.group(1)
        # Count commits between HEAD and tag to define build
        build_commit_lines = check_output(("git", "log", tag_name + "..HEAD",
                                           "--pretty=oneline")
                                         ).decode().split("\n")
        self.build = str(len([True for line in build_commit_lines]) - 1)

        self.branch = check_output(("git", "rev-parse",
                                    "--abbrev-ref", "HEAD")).decode().strip()

        # Write version to meta module
        with open("mauzr/_meta.py", "w") as metafile:
            metafile.write("\"\"\" Autogenerated file. \"\"\"\n\n")
            metafile.write("__version__ = \"" + self.python_version + "\"\n")

    @property
    def python_version(self):
        """ Python version. """

        if self.build != "0":
            return self.version + ".post" + self.build
        return self.version

# Generate version
VERSION = VersionInfo()

class FetchCommand(setuptools.Command):
    """ Setuptools command for mauzr flashing. """
    # pylint: disable=attribute-defined-outside-init

    build = Path("build")
    """ Base directory for output. """
    description = "Flash mauzr to esp devices"
    """ Command description. """
    user_options = [("new", "b", "Board is new (erase flash)"),
                    ("board=", "b", "Board"),
                    ("port=", "p", "Port to use for upload")]
    """ Available options. """

    def initialize_options(self):
        """ Set default values for options. """

        self.board = None
        self.new = False
        self.port = "/dev/ttyUSB0"

    def finalize_options(self):
        """ Collect parameters. """

        if self.board is None:
            raise ValueError("Board must be set")
        elif self.board.startswith("esp82"):
            self.board = "eps82xx"

    def run(self):
        """ Execute command. """

        import requests
        import json

        api_url = "https://api.github.com/repos/eqrx/mauzr/releases/latest"
        info = json.loads(requests.get(api_url).text)
        boards = {}
        for a in info["assets"]:
            boards[a["name"].replace(".bin", "")] = a["browser_download_url"]

        bin_url = boards[self.board]
        bin_path = self.build/f"{self.board}.bin"
        r = requests.get(bin_url, stream=True)

        # pylint: disable=e1101
        with bin_path.open('wb') as f:
            shutil.copyfileobj(r.raw, f)

class FlashCommand(setuptools.Command):
    """ Setuptools command for mauzr flashing. """
    # pylint: disable=attribute-defined-outside-init

    build = Path("build")
    """ Base directory for output. """
    description = "Flash mauzr to esp devices"
    """ Command description. """
    user_options = [("new", "b", "Board is new (erase flash)"),
                    ("board=", "b", "Board"),
                    ("port=", "p", "Port to use for upload")]
    """ Available options. """

    def initialize_options(self):
        """ Set default values for options. """

        self.board = None
        self.new = False
        self.port = "/dev/ttyUSB0"

    def finalize_options(self):
        """ Collect parameters. """

        if self.board is None:
            raise ValueError("Board must be set")

    def run(self):
        """ Execute command. """
        baud = 1500000 if self.board.startswith("esp32-") else 921600
        offset = 0x10000 if self.board.startswith("esp32-") else 0
        if self.board.startswith("esp82"):
            bin_path = self.build/"esp82xx.bin"
        else:
            bin_path = self.build/f"{self.board}.bin"

        cmd_base = ("esptool", "-p", self.port, "-b", str(baud))

        if self.new:
            subprocess.check_call(cmd_base + ("erase_flash",))
        subprocess.check_call(cmd_base +
                              ("write_flash", str(offset), str(bin_path)))

class BuildCommand(setuptools.Command):
    """ Setuptools command to build esp binaries. """
    # pylint: disable=attribute-defined-outside-init

    build = Path("build")
    """ Base directory for output. """
    description = "Build mauzr esp binaries"
    """ Command description. """
    user_options = [("board=", "b", "Board")]
    """ Available options. """

    def initialize_options(self):
        """ Implements required method. """

        self.board = None

    def finalize_options(self):
        """ Implements required method. """

        if self.board is None:
            raise ValueError("Board must be set")

    def run(self):
        """ Print python version of build. """

        if self.board.startswith("esp82"):
            image = "eqrx/mauzr-build-esp82xx"
            build_path = self.build/"esp82xx"
            container_cmd = "rm -rf /opt/mauzr/build/esp82xx/* && make"
            copies = (("firmware-combined.bin", "esp82xx.bin"),)
        elif self.board.startswith("esp32"):
            image = "eqrx/mauzr-build-esp32"
            build_path = self.build/"esp32"
            if self.board == "esp32":
                copies = []
                make_cmds = []
                for v in ("WIPY", "SIPY", "DEVKITC"):
                    src = "wipy" if v == "DEVKITC" else v.lower()
                    copies.append((f"{v}/release/{src}.bin",
                                   f"esp32-{v.lower()}.bin"),)
                    make_cmds.append(f"make BOARD={v}")

                container_cmd = "&&".join(make_cmds)
            else:
                variant = self.board.split("-")[1].upper()
                container_cmd = f"make BOARD={variant}"
                copies = ((f"{variant}/release/{variant.lower()}.bin",
                           f"{self.board}.bin"),)
        else:
            raise ValueError("Unknown board")

        root = Path(".").resolve()
        uid = os.geteuid()
        run_cmd = ("docker", "run", "-v", f"{root}:/opt/mauzr", image,
                   container_cmd + f" && chown {uid} -R /opt/mauzr/build")

        build_path.mkdir(parents=True, exist_ok=True)
        subprocess.check_call(("docker", "pull", image))
        subprocess.check_call(run_cmd)
        for src, dest in copies:
            shutil.copyfile(build_path/src, self.build/dest)

class VersionCommand(setuptools.Command):
    """ Setuptools command to get version information. """

    description = "Get version information"
    """ Command description. """
    user_options = []
    """ Available options. """

    def initialize_options(self):
        """ Implements required method. """

    def finalize_options(self):
        """ Implements required method. """

    @staticmethod
    def run():
        """ Print python version of build. """
        print(VERSION.python_version)

setuptools.setup(
    version=VERSION.python_version,
    author="Alexander Sowitzki",
    author_email="dev@eqrx.net",
    url="http://mauzr.eqrx.net",
    name='mauzr',
    keywords="agent cps distributed framework hardware iot mqtt smart",
    description="Framework for developing cyber-physical systems and"
                " IoT devices",
    packages=setuptools.find_packages(),
    cmdclass={"espbuild": BuildCommand, "espfetch": FetchCommand,
              "espflash": FlashCommand, "version": VersionCommand},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Environment :: X11 Applications',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: '
        'GNU Affero General Public License v3 or later (AGPLv3+)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: MicroPython',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Embedded Systems',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Hardware :: Hardware Drivers'
    ],
    setup_requires=['sphinx'],
    tests_require=['pytest', 'pylint', 'pytest-runner', 'pytest-pylint'],
    install_requires=['paho-mqtt', 'PyYAML'],
    extras_require={
        "esp flashing": ["esptool"],
        "esp fetching": ["requests"],
        "image handling": ["Pillow"],
        "rrd logging": ["rrdtool"],
        "gui": ["pygame"]
    },
    entry_points={
        "console_scripts": [
            'mauzr-picamera=mauzr.platform.raspberry.camera:main',
            'mauzr-linuxaudio=mauzr.platform.linux.audio.driver:main',
            'mauzr-imageviewer=mauzr.util.image.viewer:main',
            'mauzr-rrdlogger=mauzr.util.rrd.logger:main',
            'mauzr-rrdrenderer=mauzr.util.rrd.renderer:main'
        ]
    }
)
