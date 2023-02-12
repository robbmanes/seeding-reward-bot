import discord
import glowbot.plugins
import logging
from pkgutil import iter_modules
import tomli

CONFIG_FILE = 'config.toml'

class Bot(discord.Client):

    def __init__(self):

        intents = discord.Intents.all()
        super().__init__(intents=intents)

        self.logger = logging.getLogger('GlowBot')

        # Load configuration
        self.config = self.get_config()
    
        # Reference loaded plugins
        self.plugins = glowbot.plugins.loaded_plugins

    def get_config(self):
        try:
            with open(CONFIG_FILE, "rb") as f:
                config = tomli.load(f)
            return config
        except Exception as e:
            self.logger.fatal("Failed to parse configuration file %s: %s" % (CONFIG_FILE, e))
        
        match self.config['bot']['log_level']:
            case 'INFO':
                logging.basicConfig(level=logging.INFO)
            case 'DEBUG':
                logging.basicConfig(level=logging.DEBUG)

    async def on_ready(self):
        pass
    
    async def on_message(self, message):
        for plugin in self.plugins:
            await plugin.on_message(self, message)