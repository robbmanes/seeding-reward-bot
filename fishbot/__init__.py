import asyncio
from .config import Configuration
from .dbconnector import DBConnection
from .discord_bot import DiscordBot
import logging

_version__ = '0.1.0'


def main():
    # Parse configuration
    logging.info("Parsing configuration file...")
    try:
        config = Configuration()
    except Exception as e:
        logging.fatal("Failed to parse configuration: %s" % (e))
    
    # Set logging level
    logger = logging.getLogger(__package__)
    match config.settings['glowbot']['log_level']:
        case 'INFO':
            logger.setLevel(logging.INFO)
        case 'DEBUG':
            logger.setLevel(logging.DEBUG)

    # Open database connection
    try:
        db = DBConnection(config.settings['database'])
    except Exception as e:
        logger.fatal("Failed to initialize database: %s" % (e))

    # Start Discord bot
    bot = DiscordBot(command_prefix='!')

    logger.info("Loading discord cog extensions...")
    try:
        asyncio.run(bot.load_extensions(config.settings['discord']['discord_cogs']))
    except Exception as e:
        logger.fatal("Failed to load cogs: %s" % (e))

    logger.info("Starting discord services...")
    try:
        bot.run(config.settings['discord']['discord_token'], reconnect=True)
    except Exception as e:
        logger.fatal("Failed to run discord bot: %s" % (e))