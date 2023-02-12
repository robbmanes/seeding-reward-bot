import discord
import logging
import tomli

CONFIG_FILE = 'config.toml'

class Bot(discord.Client):

    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(intents=intents)

        self.config = self.get_config()
        match self.config['bot']['log_level']:
            case 'INFO':
                logging.basicConfig(level=logging.INFO)
            case 'DEBUG':
                logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger('GlowBot')

    def get_config(self):
        try:
            with open(CONFIG_FILE, "rb") as f:
                config = tomli.load(f)
            return config
        except Exception as e:
            self.logger.fatal("Failed to parse configuration file %s: %s" % (CONFIG_FILE, e))

    async def on_ready(self):
        self.logger.info("GlowBot initialized.")
    
    async def on_message(self, message):
        if message.author == self.user:
            return
        
        if message.content == 'ping':
            await message.channel.send('pong')