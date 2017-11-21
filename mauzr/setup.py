""" Common setuptools command for mauzr programs. """

from pathlib import Path
import shutil
import os
import subprocess
import datetime
import platform
import setuptools

class DockerCommand(setuptools.Command):
    """ Setuptools command for docker. """
    # pylint: disable=attribute-defined-outside-init

    description = "Build and push image"
    """ Command description. """
    user_options = [("slug", None, "Slug of the image")]
    """ Available options. """

    def initialize_options(self):
        """ Set default values for options. """

        self.slug = None

    def finalize_options(self):
        """ Collect parameters. """

        if self.slug is None:
            raise ValueError("Slug not set")

    def run(self):
        """ Execute command. """

        import git
        repo = git.Repo()

        if repo.is_dirty():
            raise RuntimeError("Workspace must be clean")

        branch = repo.active_branch
        commit = repo.head.object.hexsha
        arch = {"x86_64": "amd64", "armv7l": "arm"}[platform.machine()]
        timestamp = datetime.datetime.now().isoformat()

        for variant in os.listdir(".docker"):
            tags = (f"{self.slug}:{variant}-{arch}-{commit}",
                    f"{self.slug}:{variant}-{arch}-{branch}")
            subprocess.check_call(["docker", "build", "-t", tags[0],
                                   "-f", f".docker/{variant}", "--pull",
                                   "--build-arg", f"VERSION={branch}",
                                   "--build-arg", f"VCS_REF={commit}",
                                   "--build-arg", f"BUILD_DATE={timestamp}",
                                   "."])

            for tag in tags[1:]:
                subprocess.check_call(("docker", "tag", tags[0], tag))
            for tag in tags:
                subprocess.check_call(("docker", "push", tag))
            mc = ("manifest-tool", "push", "from-args", "--ignore-missing",
                  "--platforms", "linux/amd64,linux/arm",
                  "--template", f"{self.slug}:{variant}-ARCH-{commit}",
                  "--target", f"{self.slug}:{variant}-{commit}")
            mb = ("manifest-tool", "push", "from-args", "--ignore-missing",
                  "--platforms", "linux/amd64,linux/arm",
                  "--template", f"{self.slug}:{variant}-ARCH-{branch}",
                  "--target", f"{self.slug}:{variant}-{branch}")
            subprocess.check_call(mc)
            subprocess.check_call(mb)

class ESPFetchCommand(setuptools.Command):
    """ Setuptools command for mauzr flashing. """
    # pylint: disable=attribute-defined-outside-init

    build = Path("build")
    """ Base directory for output. """
    description = "Flash mauzr to esp devices"
    """ Command description. """
    user_options = [("board=", "b", "Board")]
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

class ESPFlashCommand(setuptools.Command):
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

class ESPBuildCommand(setuptools.Command):
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
