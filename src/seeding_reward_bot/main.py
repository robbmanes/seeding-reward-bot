import logging
import os

import discord

from seeding_reward_bot import db
from seeding_reward_bot.config import global_config
from seeding_reward_bot.hll_rcon_client import HLL_RCON_Client


class HLLDiscordBot(discord.Bot):
    def __init__(self, **options):
        super().__init__(**options)
        self.client = HLL_RCON_Client()

    async def close(self) -> None:
        await super().close()
        await self.client.close()


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

    # Create a hll discord bot (has an RCON client)
    bot = HLLDiscordBot()

    # Load the bot extension
    bot.load_extension("seeding_reward_bot.commands.hll")
    bot.load_extension("seeding_reward_bot.commands.hll_admin")
    bot.load_extension("seeding_reward_bot.tasks")

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
        bot.loop.run_until_complete(db.close())
        bot.loop.close()
