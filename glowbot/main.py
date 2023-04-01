import asyncio
from glowbot.config import global_config
from glowbot.db import GlowDatabase
from glowbot.hll_rcon_client import HLL_RCON_Client
import discord
from discord.ext import commands
import logging
import os
import sys
import traceback

def run_discord_bot():
    # Set logging level
    match global_config['glowbot']['log_level']:
        case 'INFO':
            logging.basicConfig(level=logging.INFO)
        case 'DEBUG':
            logging.basicConfig(level=logging.DEBUG)

    logger = logging.getLogger(__package__)
    
    # Check environment variables to override settings file
    env_token = os.environ.get('DISCORD_TOKEN')

    if env_token is not None:
        global_config['discord']['discord_token'] = env_token

    # Initialize database
    db = GlowDatabase(asyncio.get_event_loop())

    # Create a discord bot
    bot = commands.Bot(command_prefix='!')

    # Provide the discord bot with an RCON client:
    bot.client = HLL_RCON_Client()

    # Load the bot extension
    bot.load_extension('glowbot.commands')
    bot.load_extension('glowbot.tasks')

    # Actually run the bot.
    logger.info("Starting discord services...")
    try:
        bot.run(global_config['discord']['discord_token'], reconnect=True)
    except Exception as e:
        logger.fatal("Failed to run discord bot: %s" % (e))
        traceback.print_exc()

if __name__ == '__main__':
    sys.exit(0)