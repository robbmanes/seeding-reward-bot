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

        # Open an aiohttp session per RCON endpoint
        self.sessions = {}
        for rcon_server_url in self.bot.config['hell_let_loose']['rcon_url']:
            self.sessions[rcon_server_url] = aiohttp.ClientSession()

    
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
        message = f'Seeding stats for {ctx.author.mention}:'
        message += f'\n 🌱 Total seeding time (hours): `{player.total_seeding_time}`'
        message += f'\n 🏦 Unspent seeding time balance: `{player.seeding_time_balance}`'
        message += f'\n 🕰️ Last seeding time: `{player.last_seed_check}`'
        message += f'\n ℹ️ Turn your seeding hours into VIP time with `/hll claim`. '
        await ctx.respond(message)

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

        # We need to ensure we get the same VIP states for both RCON's.
        vip_dict = await self.get_vip(player.steam_id_64)
        vip_entries = []
        for key, vip in vip_dict.items():
            vip_entries.append(vip)

        if all(val != vip_entries[0] for val in vip_entries):
            # VIP from all RCON's didn't match, notify.
            await ctx.respond(f'{ctx.author.mention}: It looks like your VIP status is different between servers, please contact an admin.')
            return

        # All is well, return to the (identical) first in the list
        vip = vip_entries.pop()

        if vip == None or vip['vip_expiration'] == None:
            await ctx.respond(f'No VIP record found for {ctx.author.mention}.')
            return  

        # For some reason, the vip_expiration field drops the .f requirement in the format here.
        expiration = datetime.strptime(vip['vip_expiration'], "%Y-%m-%dT%H:%M:%S%z")
        if expiration.timestamp() < datetime.now().timestamp():
            await ctx.respond(f'{ctx.author.mention}: your VIP appears to have expired.')
            return
        await ctx.respond(f'{ctx.author.mention}: your VIP expiration date is `{expiration}`')

    @hll.command()
    async def claim(self, ctx: discord.ApplicationContext, hours: Option(
            int,
            "Redeem seeding hours for VIP status",
            required=False,
        )
    ):
        """Redeem seeding hours for VIP status"""
        await ctx.defer()
        if hours is None:
            vip_value = self.bot.config['hell_let_loose']['seeder_vip_reward_hours']
            message = f'{ctx.author.mention}:'
            message += f'\n💵 Use `/hll claim $HOURS` to turn seeding hours into VIP status.'
            message += f'\n🚜 One hour of seeding time is `{vip_value}` hour(s) of VIP status.'
            message += f'\nℹ️ Check your seeding hours with `/hll seeder`.'
            await ctx.respond(message)
        else:
            query_set = await HLL_Player.filter(discord_id__contains=ctx.author.id)
            if len(query_set) == 0:
                message = f'{ctx.author.mention}: Can\'t find your ID to claim VIP.'
                message += f'\nMake sure you have run `/hll steam64id` and registered your Steam and Discord.'
                await ctx.respond(message)
            elif len(query_set) != 1:
                self.logger.fatal("Multiple discord_id's found for %s!" % (ctx.author.id))
                await ctx.respond(f'Problem when looking up your steam/discord: multiple results found. Please ping an administrator!')
            else:
                player = query_set[0]
                self.logger.debug(f'User \"{ctx.author.name}/{player.steam_id_64}\" is attempting to claim {hours} seeder hours from their total of {player.seeding_time_balance}.')
                if hours > int(player.seeding_time_balance):
                    await ctx.respond(f'{ctx.author.mention}: ❌ Sorry, not enough banked time to claim `{hours}` hour(s) of VIP (Currently have `{int(player.seeding_time_balance)}` banked hours).')
                else:
                    player.seeding_time_balance -= hours

                    # Check the previous VIP values from both RCON's to ensure they are identical prior to proceeding
                    vip_dict = await self.get_vip(player.steam_id_64)
                    vip_entries = []
                    for key, vip in vip_dict.items():
                        vip_entries.append(vip)
                    if all(val != vip_entries[0] for val in vip_entries):
                        # VIP from all RCON's didn't match, notify.
                        await ctx.respond(f'{ctx.author.mention}: It looks like your VIP status is different between servers, please contact an admin.')
                        return

                    # All is well, return to the (identical) first in the list
                    vip = vip_entries.pop()
                    
                    grant_value = self.bot.config['hell_let_loose']['seeder_vip_reward_hours'] * hours
                    if vip is None or vip['vip_expiration'] == None:
                        expiration = datetime.now() + timedelta(hours=grant_value)
                    else:
                        expiration = datetime.strptime(vip['vip_expiration'], "%Y-%m-%dT%H:%M:%S%z") + timedelta(hours=grant_value)

                    # Make sure all RCON grants are successful.
                    result_dict = await self.grant_vip(player.player_name, player.steam_id_64, expiration.strftime("%Y-%m-%dT%H:%M:%S%z"))
                    for rcon, result in result_dict.items():
                        if result is False:
                            self.logger.error(f'Problem assigning VIP in `claim` for \"{rcon}\": {result}')
                            await ctx.respond(f'{ctx.author.mention}: There was a problem on one of the servers assigning your VIP.')
                            return

                    await player.save()
                    message = f'{ctx.author.mention}: You\'ve added `{grant_value}` hour(s) to your VIP status.'
                    message += f'\nYou have VIP until `{expiration}`'
                    message += f'\nYour remaining seeder balance is `{int(player.seeding_time_balance) - hours}` hour(s).'
                    message += f'\n💗 Thanks for seeding! 💗'
                    await ctx.respond(message)
                    return

                self.logger.fatal(f'Failed claiming VIP for \"{ctx.author.name}/{player.steam_id_64}\: {result}')
                await ctx.respond(f'{ctx.author.mention}: There was a problem claiming VIP.')
    
    def for_each_rcon(fn):
        """
        Decorator to apply method to all RCON servers in a list.
        Will iterate through all RCON servers in a list, meaning it calls it's wrapped
        function multiple times (once per server).

        This decorator additionally handles auth to the RCON's.

        Methods that call methods wrapped in this decorator should *always* expect a dict reply where the key of the
        dict is the RCON URL and the value is the return of the function.

        Ideally this method is adapted later to handle comparison of the values from different RCON's via a standard reply
        but for now the caller has to evaluate the returned dict themselves.
        """
        async def wrapper(self, *args):
            ret_vals = {}
            for rcon_server_url, session in self.sessions.items():
                self.logger.debug(f'Executing \"{fn.__name__}\" with RCON \"{rcon_server_url}\" as an endpoint...')
                res = await self.handle_rcon_auth(rcon_server_url, session)
                try:
                    res = await fn(self, rcon_server_url, session, *args)
                    ret_vals[rcon_server_url] = res
                except Exception as e:
                    raise
                # We need to check if the return value is identical for each RCON.
                # If it is not, error/alert to avoid deviant behavior.
                
            return ret_vals
        return wrapper

    async def handle_rcon_auth(self, rcon_server_url, session):
        """
        Takes a session and checks authentication to an endpoint.
        """
        async with session.get(
            '%s/api/is_logged_in' % (rcon_server_url)
        ) as response:
            r = await response.json()
            if r['result']['authenticated'] == False:
                async with session.post(
                    '%s/api/login' % (rcon_server_url),
                    json={
                        'username': self.bot.config['hell_let_loose']['rcon_user'],
                        'password': self.bot.config['hell_let_loose']['rcon_password'],
                    },
                ) as response:
                    r = await response.json()
                    if r['failed'] is False:
                        self.bot.logger.info(f'Successful RCON login to {rcon_server_url}')
                    else:
                        self.bot.logger.error(f'Failed to log into {rcon_server_url}: \"{r}\"')

    @tasks.loop(minutes=SEEDING_INCREMENT_TIMER)
    @for_each_rcon
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
    
    @for_each_rcon
    async def grant_vip(self, rcon_server_url, session, name, steam_id_64, expiration):
        """
        Add a new VIP entry to the RCON instances or update an existing entry.

        Must supply the RCON server arguments:
        name -- user's name in RCON
        steam_id_64 -- user's `steam64id`
        expiration -- time VIP expires

        Returns True for success, False for failure.
        """
        async with session.post(
            '%s/api/do_add_vip' % (rcon_server_url),
            json={
                'name': name,
                'steam_id_64': str(steam_id_64),
                'expiration': expiration,
            }
        ) as response:
            result = await response.json()
            if result['result'] == 'SUCCESS':
                self.logger.debug(f'Granted VIP to user \"{name}/{steam_id_64}\", expiration {expiration}')
                return True
            else:
                self.logger.error(f'Failed to update VIP user on \"{rcon_server_url}\": {result}')
                return False

    @for_each_rcon
    async def revoke_vip(self, rcon_server_url, session, name, steam_id_64):
        """Completely remove a VIP entry from the RCON instances."""
        async with session.post(
            '%s/api/do_remove_vip' % (rcon_server_url),
            json={
                'name': name,
                'steam_id_64': int(steam_id_64),
            }
        ) as response:
            result = await response.json()
            if result['result'] == 'SUCCESS':
                self.logger.debug(f'Revoked VIP for user {name}/{steam_id_64}')
                return True
            else:
                self.logger.error(f'Failed to remove VIP user on "\{rcon_server_url}\": {result}')
                return False
    
    @for_each_rcon
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
        pass

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