""" Common setuptools command for mauzr programs. """

from pathlib import Path
import shutil
import os
import subprocess
import setuptools

__author__ = "Alexander Sowitzki"


class DockerCommand(setuptools.Command):
    """ Setuptools command for docker. """
    # pylint: disable=attribute-defined-outside-init

    description = "Build and push image"
    """ Command description. """
    user_options = []
    """ Available options. """

    def initialize_options(self):
        """ Set default values for options. """

    def finalize_options(self):
        """ Collect parameters. """

        import git
        repo = git.Repo()

        if repo.is_dirty():
            raise RuntimeError("Workspace must be clean")

        self.commit = repo.head.object.hexsha

    def run(self):
        """ Execute command. """

        for variant in os.listdir(".docker"):
            hooks_kwargs = {"cwd": ".docker/"+variant,
                            "env": {"GIT_SHA1": self.commit}}

            subprocess.check_call(("./hooks/build",), **hooks_kwargs)
            subprocess.check_call(("./hooks/push",), **hooks_kwargs)
            subprocess.call(("./hooks/build",), **hooks_kwargs)


class ESPBuildCommand(setuptools.Command):
    """ Setuptools command to build esp binaries. """
    # pylint: disable=attribute-defined-outside-init

    description = "ESP maangement"
    """ Command description. """
    user_options = [("nopull", "np", "Not pull build images")]
    """ Available options. """

    def initialize_options(self):
        """ Implements required method. """

        self.nopull = False

    def finalize_options(self):
        """ Implements required method. """

    def run(self):
        """ Print python version of build. """
        image = "eqrx/mauzr-build:esp"
        root = Path(".").resolve()
        uid = os.geteuid()
        cmd = ("make -C esp32 && rm -rf esp8266/build/* &&" +
               "make -C esp8266 && chown {} -R /opt/mauzr/build".format(uid))
        run_cmd = ("docker", "run", "-v", root+":/opt/mauzr",
                   image, "sh", "-c", cmd)

        (root/"build"/"esp"/"32").mkdir(parents=True, exist_ok=True)
        (root/"build"/"esp"/"8266").mkdir(parents=True, exist_ok=True)
        if not self.nopull:
            subprocess.check_call(("docker", "pull", image))
        subprocess.check_call(run_cmd)


class ESPFlashCommand(setuptools.Command):
    """ Setuptools command for esp. """
    # pylint: disable=attribute-defined-outside-init

    image = "eqrx/mauzr-build:esp"
    steps = ((("esp8285",), "export FLASH_MODE=dout"),
             (("esp8266", "esp8285"), "rm -rf esp8266/build/*"),
             (("esp8266", "esp8285"), "make -C esp8266 all"),
             (("esp32",), "make -C esp32"))

    description = "Flash mauzr to esp devices"
    """ Command description. """
    user_options = [("erase", "e", "Board is new (erase flash)"),
                    ("board=", "b", "Board"),
                    ("port=", "p", "Port to use for upload"),
                    ("nopull", "np", "Not pull build images")]
    """ Available options. """

    def initialize_options(self):
        """ Set default values for options. """

        self.board = None
        self.erase = False
        self.port = None

    def finalize_options(self):
        """ Collect parameters. """

        cmd = "export PORT={} && ".format(self.port)
        cmd += " && ".join([step for boards, step in self.steps
                            if self.board in boards])
        if self.erase:
            cmd += "erase "
        if self.port is not None:
            cmd += "deploy "
        cmd += " && chown {} -R /opt/mauzr/build".format(os.geteuid())
        self.cmd = cmd

    def run(self):
        """ Execute command. """

        root = Path(".").resolve()
        (root/"build"/"esp"/"32").mkdir(parents=True, exist_ok=True)
        (root/"build"/"esp"/"8266").mkdir(parents=True, exist_ok=True)
        run_cmd = ("docker", "run", "--privileged", "-v", root+":/opt/mauzr",
                   self.image, "sh", "-c", self.cmd)
        subprocess.check_call(("docker", "pull", self.image))
        subprocess.check_call(run_cmd)


class ESPDeployCommand(setuptools.Command):
    """ Setuptools command for upy deployment. """
    # pylint: disable=attribute-defined-outside-init

    BUILD_BASE = Path("build")
    """ Base directory for output. """

    description = "Deploy upy sources"
    """ Command description. """
    user_options = [("id=", "i", "ID of the unit"),
                    ("module=", "m", "Main module of the unit"),
                    ("port=", "p", "Port to use for upload")]
    """ Available options. """

    def initialize_options(self):
        """ Set default values for options. """

        self.id = None
        self.module = None
        self.port = "/dev/ttyUSB0"

    def finalize_options(self):
        """ Collect parameters. """

        if self.id is None:
            raise ValueError("ID must be set")
        self.build = self.BUILD_BASE / self.id
        self.id = self.id.split("-")
        if self.module is None:
            raise ValueError("Module must be set")
        self.module = Path(self.module)

    def run(self):
        """ Execute command. """

        from mauzr.platform.cpython.config import Config

        shutil.rmtree(self.build, ignore_errors=True)
        self.build.mkdir(parents=True)

        cfg = Config(*self.id).read_config()
        if len(cfg) <= 1:
            raise ValueError("No config found")

        cfg_path = self.build / "config.py"
        cfg_path.open("w").write(repr(cfg))

        cfg = (None, cfg_path)
        main = (self.module, self.build/"main.py")
        cert = (Path("/etc/ssl/certs/DST_Root_CA_X3.pem"),
                self.build/"cert"/"ca.pem")

        for src, dest in (main, cert):
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)

        cmd = ["ampy", "-p", self.port, "put"]
        subprocess.check_call(cmd + ["main.py"], cwd=self.build)
        subprocess.check_call(cmd + ["config.py"], cwd=self.build)
