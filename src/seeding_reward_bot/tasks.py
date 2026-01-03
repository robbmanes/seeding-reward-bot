import asyncio
import logging
from datetime import datetime, time, timedelta, timezone

from discord.ext import commands, tasks
from tortoise.exceptions import DoesNotExist

from seeding_reward_bot.config import global_config
from seeding_reward_bot.db import HLL_Player
from seeding_reward_bot.main import HLLDiscordBot

# Minutes - how often the RCON is queried for seeding checks
SEEDING_INCREMENT_TIMER = 3


class BotTasks(commands.Cog):
    """
    Cog to handle bot tasks/scheduling.
    """

    def __init__(self, bot: HLLDiscordBot):
        self.bot = bot
        self.client = bot.client
        self.logger = logging.getLogger(__name__)

        self.reward_time = timedelta(minutes=SEEDING_INCREMENT_TIMER)

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
            seeding_start_time_str = global_config["hell_let_loose"][
                "seeding_start_time_utc"
            ]
            seeding_end_time_str = global_config["hell_let_loose"][
                "seeding_end_time_utc"
            ]

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
                self.logger.debug(
                    f'Not within seeding time range of "{seeding_start_time_str} - {seeding_end_time_str}" UTC'
                )
                return

        except ValueError as e:
            # If we excepted here, then the string is incorrect in fromisoformat (or something worse!)
            self.logger.error(f"Can't set seeding hours: {e}")
            pass
        except TypeError:
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
        if len(player_list) < global_config["hell_let_loose"]["seeding_threshold"]:
            self.logger.info(
                f'Server "{rcon_server_url}" qualifies for seeding status at this time.'
            )
            self.logger.debug(
                f'Returned player list for "{rcon_server_url}" is "{player_list}"'
            )

            # Iterate through current players and accumulate their seeding time
            for player in player_list:
                player_name = player["name"]
                player_id = player["player_id"]
                self.logger.debug(
                    f'Processing seeding record for player "{player_name}/{player_id}"'
                )
                try:
                    seeder = await HLL_Player.get(player_id=player_id)
                except DoesNotExist:
                    # New seeder, make a record
                    self.logger.debug(
                        f'Generating new seeder record for "{player_name}/{player_id}"'
                    )
                    seeder = HLL_Player(
                        player_id=player_id,
                        player_name=player_name,
                        seeding_time_balance=self.reward_time,
                        total_seeding_time=self.reward_time,
                        last_seed_check=datetime.now(timezone.utc),
                    )
                    try:
                        await seeder.save()
                    except Exception as e:
                        self.logger.error(
                            f'Failed creating record "{seeder.player_name}" during seeding: {e}'
                        )
                except Exception:
                    self.logger.exception(f"Failed getting record for {player_id=}")
                else:
                    # Account for seeding time for player
                    old_seed_balance = seeder.seeding_time_balance
                    seeder.player_name = player_name
                    seeder.seeding_time_balance += self.reward_time
                    seeder.total_seeding_time += self.reward_time
                    seeder.last_seed_check = datetime.now(timezone.utc)

                    try:
                        self.logger.debug(
                            f'Updating record for "{seeder.player_name}/{seeder.player_id}" to new total "{seeder.total_seeding_time}" (new seeding balance "{seeder.seeding_time_balance}")'
                        )
                        await seeder.save()
                        self.logger.debug(
                            f'Successfully updated seeding record for "{seeder.player_name}"'
                        )
                    except Exception as e:
                        self.logger.error(
                            f'Failed updating record "{seeder.player_name}" during seeding: {e}'
                        )

                    # Check if user has gained an hour of seeding awards.
                    new_hourly = seeder.seeding_time_balance // timedelta(hours=1)
                    old_hourly = old_seed_balance // timedelta(hours=1)

                    if new_hourly > old_hourly:
                        self.logger.debug(
                            f'Player "{seeder.player_name}/{seeder.player_id}" has gained 1 hour seeder rewards'
                        )
                        tg.create_task(
                            self.send_seeding_message(rcon_server_url, seeder.player_id)
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


def setup(bot: HLLDiscordBot):
    bot.add_cog(BotTasks(bot))


def teardown(bot: HLLDiscordBot):
    pass
