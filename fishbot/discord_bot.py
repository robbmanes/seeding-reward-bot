import asyncio
from .config import Configuration
import discord
from discord.ext import commands
import fishbot.cogs
import logging
import os
import traceback


class DiscordBot(commands.Bot):
    """
    Primary class representing a single discord bot belonging to a single server.
    """

    def __init__(self, command_prefix):
        intents = discord.Intents.all()
        super().__init__(command_prefix, intents=intents)

        self.logger = logging.getLogger(__package__)
    
    async def load_extensions(self, cog_list):
        for cog in cog_list:
            try:
                self.load_extension('fishbot.cogs.%s' % (cog))
                self.logger.info("Loaded cog \"%s\" successfully." % cog)
            except Exception as e:
                self.logger.error("Failed to load cog '%s': %s" % (cog, e))
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

    # Start Discord bot
    bot = DiscordBot(command_prefix='!')
    env_token = os.environ.get('DISCORD_TOKEN')

    if env_token is not None:
        config.settings['discord']['discord_token'] = env_token

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
        traceback.print_exc()

if __name__ == '__main__':
    run_discord_bot()