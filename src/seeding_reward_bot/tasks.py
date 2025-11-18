import asyncio
import logging
from datetime import datetime, time, timedelta, timezone

import discord
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands, tasks

from seeding_reward_bot.config import global_config
from seeding_reward_bot.db import HLL_Player

SEEDING_INCREMENT_TIMER = 3 # Minutes - how often the RCON is queried for seeding checks


class BotTasks(commands.Cog):
    """
    Cog to handle bot tasks/scheduling.
    """

    def __init__(self, bot):
        self.bot = bot
        self.client = bot.client
        self.logger = logging.getLogger(__name__)

        # Start tasks during init
        self.update_seeders.start()

    @tasks.loop(minutes=SEEDING_INCREMENT_TIMER)
    async def update_seeders(self):
        """
        Check if a server is in seeding status and record seeding statistics.
        If RCON reports `seeding_threshold` is not met, server qualifies as "seeding".
        Accumulate total "seeding" time for users including "unspent" seeding time to be used
        for rewards to those who seed.
        """
        # Ensure that we are during active seeding hours, if set.
        try:
            seeding_start_time_str = global_config['hell_let_loose']['seeding_start_time_utc']
            seeding_end_time_str = global_config['hell_let_loose']['seeding_end_time_utc']

            seeding_start_time = time.fromisoformat(seeding_start_time_str)
            seeding_end_time = time.fromisoformat(seeding_end_time_str)

            time_now = datetime.now(timezone.utc).time()

            # https://stackoverflow.com/questions/20518122/python-working-out-if-time-now-is-between-two-times
            def is_now(start, end, now):
                if start == end:
                    return True
                if start <= end:
                    return start <= now <= end
                else:
                    return start <= now or now < end

            if not is_now(seeding_start_time, seeding_end_time, time_now):
                self.logger.debug(f'Not within seeding time range of "{seeding_start_time_str} - {seeding_end_time_str}" UTC')
                return

        except ValueError as e:
            # If we excepted here, then the string is incorrect in fromisoformat (or something worse!)
            self.logger.error(f"Can't set seeding hours: {e}")
            pass
        except TypeError as e:
            # If we excepted here, then seeding times are undefined, carry on
            pass

        # Run once per RCON:
        async with asyncio.TaskGroup() as tg:
            for rcon_server_url in global_config["hell_let_loose"]["rcon_url"]:
                tg.create_task(self.update_seeders_per(rcon_server_url, tg))

    async def update_seeders_per(self, rcon_server_url, tg):
        player_list = await self.client.get_player_list(rcon_server_url)

        self.logger.debug(f'Processing seeding player list for "{rcon_server_url}"...')

        # Check if player count is below seeding threshold
        if len(player_list) < global_config['hell_let_loose']['seeding_threshold']:
            self.logger.info(f'Server "{rcon_server_url}" qualifies for seeding status at this time.')
            self.logger.debug(f'Returned player list for "{rcon_server_url}" is "{player_list}"')

            # Iterate through current players and accumulate their seeding time
            for player in player_list:
                player_name = player['name']
                steam_id_64 = player['player_id']
                self.logger.debug(f'Processing seeding record for player "{player_name}/{steam_id_64}"')
                seeder_query = await HLL_Player.filter(steam_id_64__contains=player['player_id'])
                if not seeder_query:
                    # New seeder, make a record
                    self.logger.debug(f'Generating new seeder record for "{player_name}/{steam_id_64}"')
                    s = HLL_Player(
                            steam_id_64=steam_id_64,
                            player_name=player_name,
                            discord_id=None,
                            seeding_time_balance=timedelta(minutes=0),
                            total_seeding_time=timedelta(minutes=0),
                            last_seed_check=datetime.now(timezone.utc),
                        )
                    await s.save()
                elif len(seeder_query) != 1:
                    self.logger.error(f'Multiple steam64id\'s found for "{steam_id_64}"!')
                else:
                    # Account for seeding time for player
                    seeder = seeder_query[0]
                    additional_time = timedelta(minutes=SEEDING_INCREMENT_TIMER)
                    old_seed_balance = seeder.seeding_time_balance
                    seeder.seeding_time_balance += additional_time
                    seeder.total_seeding_time += additional_time
                    seeder.last_seed_check = datetime.now(timezone.utc)

                    try:
                        self.logger.debug(f'Updating record for "{seeder.player_name}/{seeder.steam_id_64}" to new total "{seeder.total_seeding_time}" (new seeding balance "{seeder.seeding_time_balance}")')
                        await seeder.save()
                        self.logger.debug(f'Successfully updated seeding record for "{seeder.player_name}"')
                    except Exception as e:
                        self.logger.error(f'Failed updating record "{seeder.player_name}" during seeding: {e}')

                    # Check if user has gained an hour of seeding awards.
                    new_hourly = seeder.seeding_time_balance // timedelta(hours=1)
                    old_hourly = old_seed_balance // timedelta(hours=1)

                    if new_hourly > old_hourly:
                        self.logger.debug(f'Player "{seeder.player_name}/{seeder.steam_id_64}" has gained 1 hour seeder rewards')
                        tg.create_task(
                            self.send_seeding_message(
                                rcon_server_url, seeder.steam_id_64
                            )
                        )

            self.logger.debug(f'Seeder status updated for server "{rcon_server_url}"')
        else:
            self.logger.debug(
                f"Server {rcon_server_url} does not qualify as seeding status at this time (player_count = {len(player_list)}, must be > {global_config['hell_let_loose']['seeding_threshold']}).  Skipping."
            )

    async def send_seeding_message(self, rcon_server_url, player_id):
        if not await self.client.send_player_message(
            rcon_server_url,
            player_id,
            global_config["hell_let_loose"]["seeder_reward_message"],
        ):
            self.logger.error(
                f'Failed to send seeder reward message to player "{player_id}"'
            )

    def cog_unload(self):
        pass


def setup(bot):
    bot.add_cog(BotTasks(bot))


def teardown(bot):
    pass
