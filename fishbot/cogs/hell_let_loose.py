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
    seeder_reward_message -- `str`, message given to seeders in-game when they gain rewards
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
            'Your Steam ID (64 version, NOT 32 version)',
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
        message += f'\n 🏦 Unspent seeding time balance (hours): `{player.seeding_time_balance}`'
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

        expiration = convert_rcon_datetime(vip['vip_expiration'])
        if expiration.timestamp() < datetime.now().timestamp():
            await ctx.respond(f'{ctx.author.mention}: your VIP appears to have expired.')
            return
        await ctx.respond(f'{ctx.author.mention}: your VIP expiration date is `{expiration}`')

    @hll.command()
    async def claim(self, ctx: discord.ApplicationContext, hours: Option(
            int,
            'Redeem seeding hours for VIP status',
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
                if hours > player.seeding_time_balance.seconds // 3600:
                    await ctx.respond(f'{ctx.author.mention}: ❌ Sorry, not enough banked time to claim `{hours}` hour(s) of VIP (Currently have `{player.seeding_time_balance.seconds // 3600}` banked hours).')
                    return
                else:
                    player.seeding_time_balance -= timedelta(hours=hours)

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
                        expiration = convert_rcon_datetime(vip['vip_expiration']) + timedelta(hours=grant_value)

                    # Make sure all RCON grants are successful.
                    result_dict = await self.grant_vip(player.player_name, player.steam_id_64, expiration.strftime("%Y-%m-%dT%H:%M:%S%z"))
                    for rcon, result in result_dict.items():
                        if result is False:
                            self.logger.error(f'Problem assigning VIP in `claim` for \"{rcon}\": {result}')
                            await ctx.respond(f'{ctx.author.mention}: There was a problem on one of the servers assigning your VIP.')
                            return

                    message = f'{ctx.author.mention}: You\'ve added `{grant_value}` hour(s) to your VIP status.'
                    message += f'\nYou have VIP until `{expiration}`'
                    message += f'\nYour remaining seeder balance is `{player.seeding_time_balance}` hour(s).'
                    message += f'\n💗 Thanks for seeding! 💗'
                    await player.save()
                    await ctx.respond(message)
                    return

                self.logger.fatal(f'Failed claiming VIP for \"{ctx.author.name}/{player.steam_id_64}\: {result}')
                await ctx.respond(f'{ctx.author.mention}: There was a problem claiming VIP.')

    def for_single_rcon(fn):
        """
        Decorator to apply method to only ever work on a singe RCON server,
        like sending a player a message (since they can't be logged in to two
        HLL instances at once).

        This decorator handles auth to the RCON for the session.
        """
        async def wrapper(self, rcon_server_url, session, *args):
            res = await self.handle_rcon_auth(rcon_server_url, session)
            self.logger.debug(f'Executing \"{fn.__name__}\" with RCON \"{rcon_server_url}\" as an endpoint...')
            res = await fn(self, rcon_server_url, session, *args)
            return res
        return wrapper

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
                res = await self.handle_rcon_auth(rcon_server_url, session)
                try:
                    self.logger.debug(f'Executing \"{fn.__name__}\" with RCON \"{rcon_server_url}\" as an endpoint...')
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

            # Check if player count is below seeding threshold
            if len(player_list) < self.bot.config['hell_let_loose']['seeding_threshold']:
                self.logger.debug(f'Server \"{rcon_server_url}\" qualifies for seeding status at this time.')

                # Iterate through current players and accumulate their seeding time
                for player in player_list['result']:
                    seeder_query = await HLL_Player.filter(steam_id_64__contains=player['steam_id_64'])
                    player_name = player['name']
                    steam_id_64 = player['steam_id_64']
                    if not seeder_query:
                        # New seeder, make a record
                        self.logger.debug(f'Generating new seeder record for \"{player_name}/{steam_id_64}\"')
                        s = HLL_Player(
                                steam_id_64=steam_id_64,
                                player_name=player_name,
                                discord_id=None,
                                seeding_time_balance=timedelta(minutes=0),
                                total_seeding_time=timedelta(minutes=0),
                                last_seed_check=datetime.now(),
                            )
                        await s.save()
                    elif len(seeder_query) != 1:
                        self.logger.error(f'Multiple steam64id\'s found for \"{steam_id_64}\"!')
                    else:
                        # Account for seeding time for player
                        seeder = seeder_query[0]
                        additional_time = timedelta(minutes=SEEDING_INCREMENT_TIMER)
                        old_seed_balance = seeder.seeding_time_balance
                        seeder.seeding_time_balance += additional_time
                        seeder.total_seeding_time += additional_time
                        seeder.last_seed_check = datetime.now()

                        try:
                            await seeder.save()
                            self.logger.debug(f'Successfully updated seeding record for \"{seeder.player_name}\"')
                        except Exception as e:
                            self.logger.error(f'Failed updating record \"{seeder.player_name}\" during seeding: {e}')

                        # Check if user has gained an hour of seeding awards.
                        m, s = divmod(seeder.seeding_time_balance.seconds, 60)
                        new_hourly, _ = divmod(m, 60)

                        m, s = divmod(old_seed_balance.seconds, 60)
                        old_hourly, _ = divmod(m, 60)

                        if new_hourly > old_hourly:
                            self.logger.debug(f'Player \"{seeder.player_name}/{seeder.steam_id_64}\" has gained 1 hour seeder rewards')
                            result = await self.send_player_message(
                                rcon_server_url,
                                session,
                                seeder.steam_id_64,
                                self.bot.config['hell_let_loose']['seeder_reward_message'],
                            )
                            if not result:
                                self.logger.error(f'Failed to send seeder reward message to player \"{seeder.steam_id_64}\"')

                self.logger.debug(f'Seeder status updated for server \"{rcon_server_url}\"')
            else:
                self.logger.debug("Server %s does not qualify as seeding status at this time (player_count = %s, must be > %s).  Skipping." % (
                        rcon_server_url,
                        len(player_list),
                        self.bot.config['hell_let_loose']['seeding_threshold'],
                    )
                )

    def convert_rcon_datetime(self, date_string):
        """Convert datetime strings from the RCON to datetime objects"""
        try:
            # Newer RCON entries do not have the .f field
            return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S%z")
        except ValueError as e:
            return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%f%z")

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
            result = await response.json()
            vip_list = result['result']
            for vip in vip_list:
                if int(vip['steam_id_64']) == steam_id_64:
                    return vip
        return None
    
    @for_single_rcon
    async def send_player_message(self, rcon_server_url, session, steam_id_64, message):
        """
        Send a player a message via the RCON.
        
        Returns True for success, False for failure
        """
        async with session.get(
            '%s/api/do_message_player' % (rcon_server_url),
            json={
                'steam_id_64': steam_id_64,
                'message': message,
            }
        ) as response:
            result = await response.json()
            if result['result'] == 'SUCCESS':
                return True
        self.logger.error(f'Failed sending message to user {steam_id_64}: {result}')
        return False

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
    steam_id_64 = fields.BigIntField(description='Steam64Id for the player')
    player_name = fields.TextField(description='Player\'s stored name', null=True)
    discord_id = fields.TextField(description='Discord ID for player', null=True)
    seeding_time_balance = fields.TimeDeltaField(description='Amount of unspent seeding hours')
    total_seeding_time = fields.TimeDeltaField(description='Total amount of time player has spent seeding')
    last_seed_check = fields.DatetimeField(description='Last time the seeder was seen during a seed check')

    def __str__(self):
        if self.player_name is not None:
            return self.player_name
        else:
            return self.steam_id_64

def setup(bot):
    bot.add_cog(HellLetLoose(bot))

def teardown(bot):
    pass