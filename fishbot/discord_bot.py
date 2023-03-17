import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .config import Configuration
import discord
from discord.ext import commands
import logging
import os
import sys
from tortoise import Tortoise
import traceback

SUPPORTED_DATABASES = ['sqlite', 'postgres']

class DiscordBot(commands.Bot):
    """
    Primary class representing a single discord bot belonging to a single server.
    """

    models = ['aerich.models']
    cogs = []

    def __init__(self, command_prefix):
        intents = discord.Intents.all()
        super().__init__(command_prefix, intents=intents)

        self.logger = logging.getLogger(__package__)
    
    async def load_extensions(self):
        for cog in self.cogs:
            try:
                self.load_extension(cog)
                self.logger.info("Loaded cog \"%s\" successfully." % cog)
            except Exception as e:
                self.logger.error("Failed to load cog '%s': %s" % (cog, e))
                traceback.print_exc()
    
    async def init_db(self):
        """ Detect the type of database and attempt to initialize it with schemas. """
        # Only allow a single type of database configuration at a time
        if len(self.config['database']) != 1:
            self.logger.fatal("Multiple database configurations detected; only have a single database configuration!")
            raise Exception
        
        if not any(set(self.config['database'].keys()).intersection(SUPPORTED_DATABASES)):
            self.logger.fatal("No supported database type found in configuration. Supported types are %s." %
                              (SUPPORTED_DATABASES))
            raise Exception

        # Build a db_config for init
        if 'sqlite' in self.config['database']:
            db_config = {
                'connections': {
                    'default': 'sqlite://%s' % (self.config['database']['sqlite']['db_file'])
                },
                'apps': {
                    'fishbot': {
                        'models': self.models,
                    },
                },
            }
        elif 'postgres' in self.config['database']:
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
                    'fishbot': {
                        'models': self.models,
                        'default_connection': 'default',
                    },
                },
            }
        else:
            # Theoretically we don't ever get here, I hope
            self.logger.fatal("Invalid database driver type: %s" % 
                              (self.config['database'].keys()[0]))
            raise Exception

        self.logger.info("Loading ORM for models: %s" % (self.models))
        await Tortoise.init(config=db_config)
        await Tortoise.generate_schemas()
    
    def load_config(self, config):
        self.config = config

        # Load a cog list for loading and db init
        for cog in self.config['discord']['discord_cogs']:
            cog_path = 'fishbot.cogs.%s' % (cog)
            self.cogs.append(cog_path)
            self.models.append(cog_path)

    async def init_bot(self):
        """
        Entrypoint in the class to run the Discord bot.
        It is async to ensure a single event loop for both py-cord and asyncpg.
        """
        # Load cogs first, THEN database, to prevent wiping Meta from Models
        self.logger.info("Loading discord cog extensions...")
        try:
           await self.load_extensions()
        except Exception as e:
            self.logger.fatal("Failed to load cogs: %s" % (e))
            traceback.print_exc()

        self.logger.info("Performing database initialization for cogs...")
        try:
            await self.init_db()
        except Exception as e:
            self.logger.fatal("Failed to initialize database: %s" % (e))
            traceback.print_exc()

        self.logger.info("Adding apscheduler into event loop...")
        try:
            self.scheduler = AsyncIOScheduler()
        except Exception as e:
            self.logger.fatal("Failed to load event scheduler: %s" % (e))
            traceback.print_exc()


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
    match config.settings['fishbot']['log_level']:
        case 'INFO':
            logger.setLevel(logging.INFO)
        case 'DEBUG':
            logger.setLevel(logging.DEBUG)
    
    # Check environment variables to override settings file
    env_token = os.environ.get('DISCORD_TOKEN')
    print(env_token)

    if env_token is not None:
        config.settings['discord']['discord_token'] = env_token

    # Discord bot logic
    bot = DiscordBot(command_prefix='!')

    # We load the configuration as late as possible to allow for customization.
    bot.load_config(config.settings)

    # Load in the event loop for the database and cog initialization
    loop = asyncio.get_event_loop()
    bot.loop = loop
    loop.run_until_complete(bot.init_bot())

    # Actually run the bot.
    logger.info("Starting discord services...")
    try:
        bot.run(bot.config['discord']['discord_token'], reconnect=True)
    except Exception as e:
        logger.fatal("Failed to run discord bot: %s" % (e))
        traceback.print_exc()


if __name__ == '__main__':
    run_discord_bot()
