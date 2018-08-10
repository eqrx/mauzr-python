""" Basics to implement an agent. """

import weakref
import re
from contextlib import contextmanager, ExitStack, suppress
from mauzr.mqtt import MQTTOfflineError
from mauzr.serializer import Serializer, Struct, Topic, String

__author__ = "Alexander Sowitzki"


class Agent:
    """ Base class for all mauzr agents.

    An agent has a single responsibility and works with other agents in
    a system to fulfill a higher target.

    The agent currently take two positional arguments: The shell of the agent
    and the name of the agent.
    """

    def __init__(self, shell, name):
        self.shell, self.name, self.sched = shell, name, shell.sched

        cfg_topic = f"cfg/{shell.name}/{name}"
        assert name != "+"
        cfg_handle = shell.mqtt(topic=cfg_topic, qos=1, retain=True,
                                ser=String(shell=shell,
                                           desc="Configuration entries"))

        status_topic = f"status/{shell.name}/{name}"
        status_ser = Struct(shell=shell, fmt="B", desc="Is this agent active")

        self.cfg_handle = cfg_handle
        self.status_handle = shell.mqtt(topic=status_topic, qos=1, retain=True,
                                        ser=status_ser)
        self.__armed = False
        self.options = {}
        self.__contexts = []
        self.__inputs = {}
        self.__input_subs = {}
        self.__missing_inputs = set()
        self.__cfg_subs = {}
        self.__stack = ExitStack()

        self.active = False  # Indicates if agent is active.

        self.log = shell.log.getChild(name)  # Logger for this agent.

        weakref.finalize(self, self.log.info, "Finalized")

        with suppress(MQTTOfflineError):
            self.status_handle(False)
        # Make log level of agent an option.
        self.option("log_level", "str", "Log level of the agent",
                    cb=lambda l: self.log.setLevel(l.upper()),
                    restart=False, default="info")
        super().__init__()
        self.shell.add_agent(self)


    def is_ready(self):
        """ True if agent is ready to be activated. """

        # If no missing topics are present the agent is ready.
        return not self.__missing_inputs and self.__armed

    def __getattr__(self, name):
        """ Map agent options to object attributes. """

        try:
            return self.options[name]
        except KeyError:
            raise AttributeError

    def __enter__(self):
        """ Transition agent to active state. """

        assert not self.active

        if not self.is_ready():
            raise RuntimeError("Agent not ready")

        [self.__stack.enter_context(c()) for c in self.__contexts]

        for handle, (cbs, kwargs) in self.__inputs.items():
            l = self.__input_subs.setdefault(handle, [])
            l.extend([handle.sub(cb, **kwargs) for cb in cbs])

        self.active = True
        with suppress(MQTTOfflineError):
            self.status_handle(True)
        return self

    def __exit__(self, *exc_details):
        """ Transistion agents to inactive. """

        self.__stack.close()
        self.__input_subs.clear()

        self.active = False
        with suppress(MQTTOfflineError):
            self.status_handle(False)

    def guard_error(self, cb):
        """ Suppress any exception on the callback and stop the agent if any.

        Args:
            cb (callable): Callable to guard.
        Returns:
            callable: Wrapper callable.
        """

        def _guard(*args, **kwargs):
            try:
                cb(*args, **kwargs)
            except Exception:  # pylint: disable=broad-except
                # Log into logger.
                self.log.exception("Unhandled error occured")
                # Restart agent on error.
                self.update_agent(restart=True)
                raise
        #return _guard
        return cb

    def __add_missing_input(self, handle):
        """ Register a setup topic to be required for the agent to function.

        Args:
            handle (mauzr.mqtt.Handle): Handle to register.
        """

        assert handle.topic.startswith("cfg/"), f"Invalid topic: {handle.topic}"

        self.__missing_inputs.add(handle)  # Add to missing list.
        self.update_agent()

    def __rm_missing_input(self, handle):
        assert handle.topic.startswith("cfg/"), f"Invalid topic: {handle.topic}"
        self.__missing_inputs.discard(handle)

        self.log.debug("Missing options are %s",
                       [h.topic for h in self.__missing_inputs])
        self.update_agent()

    def update_agent(self, restart=False, discard=False, arm=False):
        """ Update the state of this agent.

        Args:
            restart (bool): Force restart.
            discard (bool): Discard the agent.
            arm (bool): Arm this agent.
        """

        if arm and not self.__armed:
            self.__armed = True
            self.add_context(self.setup)

        if restart:
            self.log.info("Restarting")

        if self.active and (not self.is_ready() or restart or discard):
            self.__exit__()
            self.log.info("Deactivated")

        if discard:
            self.__cfg_subs.clear()
            self.__contexts.clear()
            self.log.info("Discarded")
            return

        if not self.active and self.is_ready():
            self.__enter__()
            self.log.info("Activated")

    def add_context(self, context):
        """ Add a context that is entered and exited by the agent.

        Args:
            context (callable): Context manager to add.
        """

        self.__contexts.append(context)
        if self.active:
            self.__stack.enter_context(context())

    def every(self, delay, cb, *args, **kwargs):
        """ Create task that will be executed regulary with delay in between.

        Must be enabled first.

        Args:
            delay (float): Delay between executions.
            cb (callable): Callable to call when timer fires.
            args (tuple): Positional arguments for callable.
            kwargs (dict): Keyword arguments for callable.
        Returns:
            Task: Created task.
        """

        return self.sched.every(delay, self.guard_error(cb), *args, **kwargs)

    def after(self, delay, cb, *args, **kwargs):
        """ Create a task that will be executed once after the given delay.

        Must be enabled first.

        Args:
            delay (float): Delay to the execution.
            cb (callable): Callable to call when timer fires.
            args (tuple): Positional arguments for callable.
            kwargs (dict): Keyword arguments for callable.
        Returns:
            Task: Created task.
        """

        return self.sched.after(delay, self.guard_error(cb), *args, **kwargs)

    def option(self, name, fmt, desc,
               ser=None, cb=None, attr=None, restart=True, default=None):
        """ Setup an option for this agent.

        Args:
            name (str): Name by this option is configured by.
            fmt (str): Required format for this option.
            desc (str): Description of this option.
            ser (mauzr.serializer.Serializer): Override serializer.
            cb (callback): Callback that is called when the option changes.
            attr (str): Attribute name of resulting field.
            restart (bool): Restart agent if option changes.
            default (object): Default value to assume for this option.
        """

        if ser is None:
            ser = Serializer.from_well_known(shell=self.shell,
                                             fmt=fmt, desc=desc)
        if attr is None:
            attr = name
        handle = self.cfg_handle.child(topic=name, ser=ser, qos=1, retain=True)

        def _cb(value):
            if value is None:
                self.log.info("Option reset: %s", handle.topic)
                self.__add_missing_input(handle)
                return
            assert value is not None

            self.options[attr] = value  # Simply set value.
            # Got message on topic, not missing anymore.
            self.__rm_missing_input(handle)
            if cb is not None:
                self.guard_error(cb)(value)

            if restart:
                self.update_agent(restart=True)

        self.__cfg_subs[name] = handle.sub(_cb)
        self.__add_missing_input(handle)

        if default is not None:
            _cb(default)
            self.__rm_missing_input(handle)

    def input_topic(self, name, regex, desc, ser=None,
                    cb=None, restart=True, sub=None):
        """ Setup a dynamic input topic.

        Args:
            name (str): Name by this topic is configured by.
            regex (str): Regex that needs to be matched by the format of the \
                         configured input.
            desc (str): Description of this topic.
            ser (mauzr.serializer.Serializer): Override configured serializer.
            cb (callable): Callable that receives messages.
            restart (bool): Restart agent if output changes.
            sub (dict): Arguments passed to mauzr.mqtt.Handle.sub.
        """

        cfg_ser = Topic(self.shell, desc)
        cfg_handle = self.cfg_handle.child(name, ser=cfg_ser,
                                           qos=1, retain=True)
        sub = sub if sub else {}

        def _source_cb(handle):
            if handle is None:
                self.log.info("Input reset: %s", cfg_handle.topic)
                self.__add_missing_input(cfg_handle)
                return

            fmt = handle.ser.fmt
            if not re.fullmatch(regex, fmt):
                raise ValueError(f"Format {fmt} does not match {regex}.")
            if ser is not None:
                handle.change_ser(ser)

            # Stop agent if it was active and restart was configured.
            if restart:
                self.update_agent(restart=True)

            self.static_input(handle, cb, sub)

            # Got message on topic, not missing anymore.
            self.__rm_missing_input(cfg_handle)

        self.__add_missing_input(cfg_handle)  # Add source to missing topics
        guarded_cb = self.guard_error(_source_cb)
        self.__cfg_subs[name] = cfg_handle.sub(guarded_cb)

    def static_input(self, handle, cb, sub=None):
        """ Setup a static input.

        Args:
            handle (mauzr.mqtt.Handle): Handle to use for input.
            cb (callable): Callback that receives messages.
            sub (dict): Arguments passed to mauzr.mqtt.Handle.sub.
        """

        if sub is None:
            sub = {}
        cb = self.guard_error(cb if callable(cb) else self.on_input)

        # Add input
        self.__inputs.setdefault(handle, ([], sub))[0].append(cb)
        # Sub to topic if already active.
        if self.active:
            l = self.__input_subs.setdefault(handle, [])
            l.append(handle.sub(cb, **sub))

    def rm_static_input(self, handle):
        """ Remove a static input from the input list (not the sub).

        Args:
            handle (Handle): The handle to remove.
        """

        del self.__inputs[handle]
        if self.active:
            del self.__input_subs[handle]

    def output_topic(self, name, regex, desc,
                     ser=None, attr=None, restart=True):
        """ Setup a dynamic output.

        Args:
            name (str): Name by this topic is configured by.
            regex (str): Regex that needs to be matched by the format of the \
                         configured output.
            desc (str): Description of this topic.
            ser (mauzr.serializer.Serializer): Override configured serializer.
            attr (str): Attribute name of resulting handle.
            restart (bool): Restart agent if output changes.
        """

        if attr is None:
            attr = name

        cfg_ser = Topic(self.shell, desc)
        cfg_handle = self.cfg_handle.child(name, ser=cfg_ser,
                                           qos=1, retain=True)

        def _source_cb(handle):
            if handle is None:
                self.log.info("Output reset: %s", cfg_handle.topic)
                self.__add_missing_input(cfg_handle)
                return

            fmt = handle.ser.fmt
            if not re.fullmatch(regex, fmt):
                raise ValueError(f"Format {fmt} does not match {regex}.")
            if ser is not None:
                handle.change_ser(ser)

            # Stop agent if it was active and restart was configured.
            if restart:
                self.update_agent(restart=True)

            self.options[attr] = handle

            # Got message on topic, not missing anymore.
            self.__rm_missing_input(cfg_handle)

        self.__add_missing_input(cfg_handle)  # Add source to missing topics
        guarded_cb = self.guard_error(_source_cb)
        self.__cfg_subs[name] = cfg_handle.sub(guarded_cb)

    @staticmethod
    @contextmanager
    def setup():
        """ Do setup & teardown by overriding this with a contextmanager. """
        yield

    def on_input(self, *args, **kwargs):
        """ Default callback for message inputs. """

        self.log.error("Unimplemented on_input was called.")
