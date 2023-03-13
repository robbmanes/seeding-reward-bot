import discord
from discord.commands import slash_command
from discord.ext import commands
from tortoise.models import Model
from tortoise import fields

class Ping(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @slash_command(name='ping',
                   description='Send a ping, get a pong.')
    async def ping(self, ctx):
        await ctx.defer()
        user = ctx.author
        record = await PingModel.filter(uid__contains=user)
        if not record:
            p = PingModel(uid=user, ping_count=1)
            await p.save()
            count = 1
        else:
            count = record[0].ping_count + 1
            await record.update(ping_count=(record[0].ping_count + 1))
        await ctx.respond(f'Pong! {ctx.author.mention} has pinged me `{count}` times.')

class PingModel(Model):
    uid = fields.TextField()
    ping_count = fields.IntField()

    def __str__(self):
        return self.name

def setup(bot):
    bot.add_cog(Ping(bot))

def teardown(bot):
    pass