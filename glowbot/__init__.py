import asyncio
from .config import Configuration
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

    # Start Discord bot
    bot = DiscordBot(command_prefix='!')

    logging.info("Loading discord cog extensions...")
    try:
        asyncio.run(bot.load_extensions(config.settings['discord']['discord_cogs']))
    except Exception as e:
        bot.logger.fatal("Failed to load cogs: %s" % (e))

    logging.info("Starting discord services...")
    try:
        bot.run(config.settings['discord']['discord_token'], reconnect=True)
    except Exception as e:
        logging.fatal("Failed to run discord bot: %s" % (e))