import aiohttp
from datetime import datetime, timedelta
import discord
from discord.commands import Option
from discord.commands import SlashCommandGroup
from discord.ext import commands, tasks
import logging
from tortoise.models import Model
from tortoise import fields

SEEDING_INCREMENT_TIMER = 3 # Minutes - how often the RCON is queried for seeding checks

class HellLetLoose(commands.Cog):
    """
    Hell Let Loose Discord.Cog for fishbot.

    Cog to manage game interactions with Hell Let Loose via the API's
    available from [Hell Let Loose Community RCON](https://github.com/MarechJ/hll_rcon_tool).

    Configuration options in fishbot's config.toml:
    ```
    [hell_let_loose]
    rcon_url -- `list`, HTTP/S RCON server URLs
    rcon_user -- `str`, username for login to RCON
    rcon_password -- `str`, password for login to RCON
    seeding_threshold -- `int`, number of players a server must exceed to no longer count as seeding
    seeder_vip_reward_hours -- `int`, number of hours that 1 hour of seeding time grants VIP status for
    ```
    """

    hll = SlashCommandGroup('hll')

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.update_seeders.start()
        self.session = aiohttp.ClientSession()
    
    @hll.command()
    async def steam64id(self, ctx: discord.ApplicationContext, steam64: Option(
            str,
            "Your Steam ID (64 version, NOT 32 version)",
            required=True,
        )
    ):
        """Register your discord account to your steam64Id"""

        await ctx.defer()
        query_result = await HLL_Player.filter(steam_id_64=steam64)
        if len(query_result) == 0:
            await ctx.respond(f'I can\'t find a record of your `steam64id`, have you played on our Hell Let Loose servers yet?')
            return
        elif len(query_result) != 1:
            self.logger.error('Player lookup during steam64id returned multiple results:')
            await ctx.respond(f'Found multiple players with that `steam64id` - that shouldn\t happen! Please contact an administrator.')
            return
        
        player = query_result[0]

        if player.discord_id is None:
            player.discord_id = ctx.author.id
            await player.save()
            self.logger.debug(f'Updated user {ctx.author.mention} with steam64id `{steam64}`')
            await ctx.respond(f'{ctx.author.mention}: I\'ve registered your `steam64id` to your Discord account. Thanks!')
            return
        elif player.discord_id == ctx.author.id:
            await ctx.respond(f'That `steam64id` is already registered to you!')
            return
        else:
            self.logger.debug(f'Discord user {ctx.author.name} attempted to register steam64id `{steam64}` but it is already owned by Discord user {player.discord_id}')
            await ctx.respond(f'That `steam64id` is already registered to someone else.')
    
    @hll.command()
    async def seeder(self, ctx: discord.ApplicationContext):
        """Check your seeding statistics"""

        await ctx.defer()
        query_result = await HLL_Player.filter(discord_id=ctx.author.id)
        if len(query_result) == 0:
            await ctx.respond(f'Your Discord ID doesn\'t match any known `steam64id`. Use `/hll steam64id` to tie your ID to your discord.')
            return
        player = query_result[0]
        await ctx.respond(f'{ctx.author.mention} has been seeding for `{player.total_seeding_time}` hours. Last seeding time was `{player.last_seed_check}`')

    @hll.command()
    async def vip(self, ctx: discord.ApplicationContext):
        """Check your VIP status"""

        await ctx.defer()
        self.logger.debug(f'VIP query for `{ctx.author.id}/{ctx.author.name}`.')
        query_result = await HLL_Player.filter(discord_id=ctx.author.id)
        if len(query_result) == 0:
            await ctx.respond(f'Your Discord ID doesn\'t match any known `steam64id`. Use `/hll steam64id` to tie your ID to your discord.')
            return
        player = query_result[0]
        vip = await self.get_vip(player.steam_id_64)
        if vip == None:
            await ctx.respond(f'No VIP record found for {ctx.author.mention}.')
            return
        expiration = datetime.strptime(vip['vip_expiration'], "%Y-%m-%dT%H:%M:%S%z")
        if expiration.timestamp() < datetime.now().timestamp():
            await ctx.respond(f'{ctx.author.mention}: your VIP appears to have expired.')
            return
        await ctx.respond(f'{ctx.author.mention}: your VIP expiration date is `{expiration}`')

    def with_rcon_session(fn):
        """
        Decorator for methods using rcon sessions.
        Ensures existing aiohttp handler is in use and subsequently ensures token is present.
        Will iterate through all RCON servers in a list, meaning it calls it's wrapped
        function multiple times (once per server).
        """
        async def wrapper(self, *args):
            for rcon_server_url in self.bot.config['hell_let_loose']['rcon_url']:
                async with self.session.get(
                    '%s/api/is_logged_in' % (rcon_server_url)
                ) as response:
                    r = await response.json()
                    if r['result']['authenticated'] == False:
                        async with self.session.post(
                            '%s/api/login' % (rcon_server_url),
                            json={
                                'username': self.bot.config['hell_let_loose']['rcon_user'],
                                'password': self.bot.config['hell_let_loose']['rcon_password'],
                            },
                        ) as response:
                            self.bot.logger.info("Successful RCON login: %s", await response.json())
                try:
                    return await fn(self, rcon_server_url, self.session, *args)
                except Exception as e:
                    raise
        return wrapper

    @tasks.loop(minutes=SEEDING_INCREMENT_TIMER)
    @with_rcon_session
    async def update_seeders(self, rcon_server_url, session):
        """
        Check if a server is in seeding status and record seeding statistics.
        If RCON reports `seeding_threshold` is not met, server qualifies as "seeding".
        Accumulate total "seeding" time for users including "unspent" seeding time to be used
        for rewards to those who seed.
        """
        async with session.get(
            '%s/api/get_players' % (rcon_server_url)
        ) as response:
            player_list = await response.json()

            if len(player_list) < self.bot.config['hell_let_loose']['seeding_threshold']:
                self.logger.debug("Server \"%s\" qualifies for seeding status at this time." % (rcon_server_url))
                # Iterate through current players and accumulate their seeding time
                for player in player_list['result']:
                    seeder_query = await HLL_Player.filter(steam_id_64__contains=player['steam_id_64'])
                    if not seeder_query:
                        s = HLL_Player(
                                steam_id_64=player['steam_id_64'],
                                player_name=player['name'],
                                discord_id=None,
                                total_seeding_time=0.0,
                                last_seed_check=datetime.now()
                            )
                        await s.save()
                    else:
                        if len(seeder_query) != 1:
                            self.logger.fatal("Multiple steam64id's found for %s!" % (player['steam_id_64']))
                            raise
                        seeder = seeder_query[0]
                        join_threshold = datetime.now() - timedelta(minutes=SEEDING_INCREMENT_TIMER)
                        if seeder.last_seed_check.timestamp() > join_threshold.timestamp():
                            seeder.seeding_time_balance = seeder.seeding_time_balance + (float(SEEDING_INCREMENT_TIMER) / 100)
                            seeder.total_seeding_time = seeder.total_seeding_time + (float(SEEDING_INCREMENT_TIMER) / 100)
                        else:
                            self.logger.debug(f'User {seeder.player_name} skipped due to being below join threshold.')

                        seeder.last_seed_check = datetime.now()
                        try:
                            await seeder.save()
                            self.logger.debug("Successfully updated seeding record for \"%s\"" % (seeder.player_name))
                        except Exception as e:
                            self.logger.error("Failed updating record \"%s\" during seeding: %s" % (seeder.player_name, e))

                    self.logger.debug("Seeder status updated for server \"%s\"" % (rcon_server_url))
            else:
                self.logger.debug("Server %s does not qualify as seeding status at this time (player_count = %s, must be > %s).  Skipping." % (
                        rcon_server_url,
                        len(player_list),
                        self.bot.config['hell_let_loose']['seeding_threshold'],
                    )
                )
    
    @with_rcon_session
    async def grant_vip(self, rcon_server_url, session, name, steam_id_64, expiration):
        """
        Add a new VIP entry to the RCON instances or update an existing entry.

        Must supply the RCON server arguments:
        name -- user's name in RCON
        steam_id_64 -- user's `steam64id`

        Returns True for success, False for failure.
        """
        async with session.post(
            '%s/api/do_add_vip' % (rcon_server_url),
            json={
                'name': name,
                'steam_id_64': steam_id_64,
                'expiration': expiration,
            }
        ) as response:
            result = await response.json()
            if result['result'] == 'SUCCESS':
                self.logger.debug(f'Granted VIP to user \"{name}/{steam_id_64}\", expiration {expiration}')
                return True
            else:
                self.logger.error(f'Failed to update VIP user on "\{rcon_server_url}\": {result}')
                return False

    @with_rcon_session
    async def revoke_vip(self, rcon_server_url, session, name, steam_id_64):
        """Completely remove a VIP entry from the RCON instances."""
        async with session.post(
            '%s/api/do_remove_vip' % (rcon_server_url),
            json={
                'name': name,
                'steam_id_64': steam_id_64,
            }
        ) as response:
            result = await response.json()
            if result['result'] == 'SUCCESS':
                self.logger.debug(f'Revoked VIP for user {name}/{steam_id_64}')
                return True
            else:
                self.logger.error(f'Failed to remove VIP user on "\{rcon_server_url}\": {result}')
                return False
    
    @with_rcon_session
    async def get_vip(self, rcon_server_url, session, steam_id_64):
        """
        Queries the RCON server for all VIP's, and returns a single VIP object
        based on the input steam64id.
        """
        async with session.get(
            '%s/api/get_vip_ids' % (rcon_server_url)
        ) as response:
            res = await response.json()
            vip_list = res['result']
            for vip in vip_list:
                if int(vip['steam_id_64']) == steam_id_64:
                    return vip
        return None

    @commands.Cog.listener()
    async def on_application_command_error(
        self, ctx: discord.ApplicationContext, error: discord.DiscordException):
        """Handle exceptions and discord errors, including permissions"""

        if isinstance(error, commands.NotOwner):
             await ctx.respond('Insufficient privileges to use that command.')
        else:
            await ctx.respond("Whoops! An internal error occurred. Please ping my maintainer!")
            raise error
    
    def cog_unload(self):
        self.bot.loop.run_until_complete(self.session.close())

class HLL_Player(Model):
    steam_id_64 = fields.BigIntField()
    player_name = fields.TextField(null=True)
    discord_id = fields.TextField(null=True)
    seeding_time_balance = fields.FloatField(default=0)
    total_seeding_time = fields.FloatField(default=0)
    last_seed_check = fields.DatetimeField()

    def __str__(self):
        if self.player_name is not None:
            return self.player_name
        else:
            return self.steam_id_64

def setup(bot):
    bot.add_cog(HellLetLoose(bot))

def teardown(bot):
    pass