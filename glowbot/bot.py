import discord
import tomli

CONFIG_FILE = 'config.toml'

class Bot(discord.Client):

    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(intents=intents)
        self.load_config()
    
    def load_config(self, config_file=None):
        try:
            with open(CONFIG_FILE, "rb") as f:
                self.config = tomli.load(f)
        except Exception as e:
            print("Failed to parse configuration file %s: %s" % (CONFIG_FILE, e.message))

    async def on_ready(self):
        print('Logged in as', self.user)
    
    async def on_message(self, message):
        if message.author == self.user:
            return
        
        if message.content == 'ping':
            await message.channel.send('pong')