import discord
from discord.commands import slash_command
from discord.ext import commands

class Ping(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @slash_command(name='ping',
                   description='Send a ping, get a pong.')
    async def ping(self, ctx):
        await ctx.respond('pong!')

def setup(bot):
    bot.add_cog(Ping(bot))

def teardown(bot):
    pass