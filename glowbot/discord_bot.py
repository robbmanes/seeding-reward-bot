import asyncio
from .config import Configuration
import discord
from discord.ext import commands
import logging
import os
import sys
from tortoise import Tortoise
import traceback

class DiscordBot(commands.Bot):
    """
    Primary class representing a single discord bot belonging to a single server.
    """

    models = ['aerich.models', 'glowbot.hell_let_loose']

    def __init__(self, command_prefix):
        intents = discord.Intents.all()
        super().__init__(command_prefix, intents=intents)

        self.logger = logging.getLogger(__package__)
    
    async def init_db(self):
        db_config = {
            'connections': {
                'default': {
                    'engine': "tortoise.backends.asyncpg",
                    'credentials': {
                        'host': self.config['database']['postgres']['db_url'],
                        'port': self.config['database']['postgres']['db_port'],
                        'user': self.config['database']['postgres']['db_user'],
                        'password': self.config['database']['postgres']['db_password'],
                        'database': self.config['database']['postgres']['db_name'],
                    },
                },
            },
            'apps': {
                'glowbot': {
                    'models': self.models,
                    'default_connection': 'default',
                },
            },
        }

        self.logger.info("Loading ORM for models: %s" % (self.models))
        await Tortoise.init(config=db_config)
        await Tortoise.generate_schemas()
    
    def load_config(self, config):
        self.config = config

def run_discord_bot():
    """primary execution point for the discord bot."""
    # Parse configuration
    logging.info("Parsing configuration file...")
    try:
        config = Configuration()
    except Exception as e:
        logging.fatal("Failed to parse configuration: %s" % (e))
        traceback.print_exc()
    
    # Set logging level
    logger = logging.getLogger(__package__)
    match config.settings['glowbot']['log_level']:
        case 'INFO':
            logger.setLevel(logging.INFO)
        case 'DEBUG':
            logger.setLevel(logging.DEBUG)
    
    # Check environment variables to override settings file
    env_token = os.environ.get('DISCORD_TOKEN')

    if env_token is not None:
        config.settings['discord']['discord_token'] = env_token

    # Discord bot logic
    bot = DiscordBot(command_prefix='!')

    # We load the configuration as late as possible to allow for customization.
    bot.load_config(config.settings)

    # Load the bot extension
    bot.load_extension('glowbot.hell_let_loose')

    # Load in the event loop for the database initialization
    loop = asyncio.get_event_loop()
    bot.loop = loop
    loop.run_until_complete(bot.init_db())

    # Actually run the bot.
    logger.info("Starting discord services...")
    try:
        bot.run(bot.config['discord']['discord_token'], reconnect=True)
    except Exception as e:
        logger.fatal("Failed to run discord bot: %s" % (e))
        traceback.print_exc()


if __name__ == '__main__':
    run_discord_bot()
