import asyncio
import logging
import os
import sys
import traceback

import discord

from seeding_reward_bot import db
from seeding_reward_bot.config import global_config
from seeding_reward_bot.hll_rcon_client import HLL_RCON_Client


def run_discord_bot():
    """
    Entry point for discord bot.
    """
    # Set logging level
    match global_config["seedbot"]["log_level"]:
        case "INFO":
            logging.basicConfig(level=logging.INFO)
        case "DEBUG":
            logging.basicConfig(level=logging.DEBUG)

    logger = logging.getLogger(__package__)

    # Check environment variables to override settings file
    env_token = os.environ.get("DISCORD_TOKEN")
    if env_token is not None:
        global_config["discord"]["discord_token"] = env_token

    env_token = os.environ.get("DISCORD_GUILD_ID")
    if env_token is not None:
        global_config["discord"]["discord_guild_id"] = env_token

    # Create a discord bot
    bot = discord.Bot()

    # Provide the discord bot with an RCON client:
    bot.client = HLL_RCON_Client()

    # Load the bot extension
    bot.load_extension("seeding_reward_bot.commands")
    bot.load_extension("seeding_reward_bot.tasks")

    # Pass in guild ID's, if there are any
    try:
        bot.guild_ids = []
        bot.guild_ids.append(global_config["discord"]["discord_guild_id"])
    except KeyError as e:
        logger.info("No guild ID's configured, proceeding...")
        pass

    # Disable Discord verbose logging - it's spammy
    logging.getLogger("discord").setLevel(logging.WARNING)

    # Actually run the bot.
    logger.info("Starting discord services...")

    # Initialize database
    bot.loop.create_task(db.init())
    try:
        bot.loop.run_until_complete(
            bot.start(global_config["discord"]["discord_token"])
        )
    except KeyboardInterrupt:
        bot.loop.run_until_complete(bot.close())
    finally:
        bot.loop.run_until_complete(bot.client.close())
        bot.loop.run_until_complete(db.close())
        bot.loop.close()


if __name__ == "__main__":
    sys.exit(0)
