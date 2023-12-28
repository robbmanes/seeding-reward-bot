import asyncio
import discord
from discord.ext import commands
from glowbot.config import global_config
from glowbot.db import GlowDatabase
from glowbot.hll_rcon_client import HLL_RCON_Client
import logging
import os
import sys
import traceback

def run_discord_bot():
    """
    Entry point for discord bot.
    """
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
    
    env_token = os.environ.get('DISCORD_GUILD_ID')
    if env_token is not None:
        global_config['discord']['discord_guild_id'] = env_token

    # Initialize database
    db = GlowDatabase(asyncio.get_event_loop())

    # Create a discord bot
    bot = commands.Bot(command_prefix='!')

    # Provide the discord bot with an RCON client:
    bot.client = HLL_RCON_Client()

    # Load the bot extension
    bot.load_extension('glowbot.commands')
    bot.load_extension('glowbot.tasks')

    # Pass in guild ID's, if there are any
    try:
        bot.guild_ids = []
        bot.guild_ids.append(global_config['discord']['discord_guild_id'])
    except KeyValue as e:
        logger.info('No guild ID\'s configured, proceeding...')
        pass

    # Disable Discord verbose logging - it's spammy
    logging.getLogger("discord").setLevel(logging.WARNING)

    # Actually run the bot.
    logger.info("Starting discord services...")
    bot.run(
        global_config['discord']['discord_token'],
        reconnect=True,
    )

if __name__ == '__main__':
    sys.exit(0)
