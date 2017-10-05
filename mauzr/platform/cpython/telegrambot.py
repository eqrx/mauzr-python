"""  Connect as a bot to telegram. """
__author__ = "Alexander Sowitzki"

import telegram.ext # pylint: disable=import-error

class Bot:
    """A telegram bot.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Configuration:**

        - **token** (:class:`str`) - Access token of the bot.
    """

    def __init__(self, core, cfgbase="telegram", **kwargs):
        core.add_context(self)

        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self.updater = telegram.ext.Updater(cfg["token"])
        self.bot = self.updater.bot
        self.dispatcher = self.updater.dispatcher

    def add_command_handler(self, command, handler):
        """ Add a new command to the bot.

        :param command: Command to handle.
        :type command: str
        :param handler: Handler function. \
          See :class:`telegram.ext.CommandHandler`
        :type handler: callable
        """

        cmd = telegram.ext.CommandHandler(command, handler)
        self.dispatcher.add_handler(cmd)

    def __enter__(self):
        self.updater.start_polling()
        return self

    def __exit__(self, *exec_details):
        self.updater.stop()
