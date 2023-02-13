import glowbot.cogs
import discord
from discord.ext import commands
import logging
import os


class DiscordBot(commands.Bot):

    def __init__(self, command_prefix):
        intents = discord.Intents.all()
        super().__init__(command_prefix, intents=intents)

        self.logger = logging.getLogger(__package__)
    
    async def load_extensions(self, cog_list):
        for cog in cog_list:
            try:
                await self.load_extension('glowbot.cogs.%s' % (cog))
            except Exception as e:
                self.logger.error("Failed to load cog '%s': %s" % (cog, e))
