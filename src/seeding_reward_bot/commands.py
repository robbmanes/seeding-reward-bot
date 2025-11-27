import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import guild_only
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands

from seeding_reward_bot.config import global_config
from seeding_reward_bot.db import HLL_Player


def get_command_mention(cmd):
    return f"</{cmd.qualified_name}:{cmd.qualified_id}>"


class BotCommands(commands.Cog):
    """
    Cog to manage discord interactions.
    """

    hll = SlashCommandGroup("hll")
    hll_admin = SlashCommandGroup("hll-admin")

    def __init__(self, bot):
        self.bot = bot
        self.client = bot.client
        self.logger = logging.getLogger(__name__)

    @hll.command()
    async def register(
        self,
        ctx: discord.ApplicationContext,
        player_id: Option(
            str,
            "Your Player ID (for Steam your SteamID64) found in the top right of OPTIONS in game",
            required=True,
        ),
    ):
        """Register your discord account to your Player ID"""

        await ctx.defer(ephemeral=True)

        # See if the user already has an entry
        query_result = await HLL_Player.filter(player_id=player_id)
        if len(query_result) > 1:
            self.logger.error(
                "Player lookup during player_id returned multiple results:"
            )
            await ctx.respond(
                "Found multiple players with that `player_id` - that shouldn't happen! Please contact an administrator.",
                ephemeral=True,
            )
            return
        elif len(query_result) == 0:
            # No entry found, provide an error message and instructions to play first
            self.logger.debug(
                f"Discord user {ctx.author.name} attempted to register player_id `{player_id}`, denied due to no record"
            )
            await ctx.respond(
                f"{ctx.author.mention}: I don't see a record for that ID; please make sure you have seeded on our servers previously and enter your Player ID (found in the top right of OPTIONS in game) to register.  Please open a ticket for additional help.",
                ephemeral=True,
            )
            return
        elif len(query_result) == 1:
            # Found one existing entry
            player = query_result[0]
            if player.discord_id is None:
                player.discord_id = ctx.author.id
                await player.save()
                self.logger.debug(
                    f"Updated user {ctx.author.mention} with player_id `{player_id}`"
                )
                await ctx.respond(
                    f"{ctx.author.mention}: I've registered your `player_id` to your Discord account. Thanks!",
                    ephemeral=True,
                )
                return
            elif player.discord_id == ctx.author.id:
                await ctx.respond(
                    "That `player_id` is already registered to you!", ephemeral=True
                )
                return
            else:
                self.logger.debug(
                    f"Discord user {ctx.author.name} attempted to register player_id `{player_id}` but it is already owned by Discord user {player.discord_id}"
                )
                await ctx.respond(
                    "That `player_id` is already registered to someone else.",
                    ephemeral=True,
                )
                return
        else:
            raise

    @hll.command()
    async def seeder(self, ctx: discord.ApplicationContext):
        """Check your seeding statistics"""

        await ctx.defer(ephemeral=True)
        query_result = await HLL_Player.filter(discord_id=ctx.author.id)
        if len(query_result) == 0:
            await ctx.respond(
                f"Your Discord ID doesn't match any known `player_id`. Use {get_command_mention(self.register)} to tie your ID to your discord.",
                ephemeral=True,
            )
            return
        player = query_result[0]
        message = f"Seeding stats for {ctx.author.mention}:"
        message += f"\n 🌱 Total seeding time (hours): `{player.total_seeding_time}`"
        message += f"\n 🏦 Unspent seeding time balance (hours): `{player.seeding_time_balance // timedelta(hours=1):,}`"
        message += (
            f"\n 🕰️ Last seeding time: <t:{int(player.last_seed_check.timestamp())}:R>"
        )
        message += f"\n ℹ️ Turn your seeding hours into VIP time with {get_command_mention(self.claim)}. One hour of seeding = {global_config['hell_let_loose']['seeder_vip_reward_hours']} hour(s) of VIP."
        await ctx.respond(message, ephemeral=True)

    @hll.command()
    async def vip(self, ctx: discord.ApplicationContext):
        """Check your VIP status"""

        await ctx.defer(ephemeral=True)
        self.logger.debug(f"VIP query for `{ctx.author.id}/{ctx.author.name}`.")
        player = await HLL_Player.by_discord_id(ctx.author.id)
        if player is None:
            await ctx.respond(
                f"Your Discord ID doesn't match any known `player_id`. Use {get_command_mention(self.register)} to tie your ID to your discord.",
                ephemeral=True,
            )
            return

        # We need to ensure we get the same VIP states for both RCON's.
        try:
            vip_dict = await self.client.get_vip(player.player_id)
        except Exception:
            await ctx.respond(
                f"{ctx.author.mention}: There was an error fetching your VIP status from one of the servers, try again later",
                ephemeral=True,
            )
            return

        vip_set = set(vip_dict.values())
        if len(vip_set) != 1:
            # VIP from all RCON's didn't match, notify.
            await ctx.respond(
                f"{ctx.author.mention}: It looks like your VIP status is different between servers, please contact an admin.",
                ephemeral=True,
            )
            return

        # All is well, return to the (identical) first in the list
        vip = vip_set.pop()

        if vip is None:
            await ctx.respond(
                f"No VIP record found for {ctx.author.mention}.", ephemeral=True
            )
            return

        expiration = datetime.fromisoformat(vip)
        if expiration < datetime.now(timezone.utc):
            await ctx.respond(
                f"{ctx.author.mention}: your VIP appears to have expired.",
                ephemeral=True,
            )
            return
        elif expiration >= datetime(year=3000, month=1, day=1, tzinfo=timezone.utc):
            # crcon uses UTC 3000-01-01 for indefinite VIP
            #   and checks with >= to test for indefinite
            # converting seeding hours is pointless in this case.
            await ctx.respond(
                f"{ctx.author.mention}: Your VIP does not expire!", ephemeral=True
            )
            return

        # https://discord.com/developers/docs/reference#message-formatting-formats
        await ctx.respond(
            f"{ctx.author.mention}: your VIP expires <t:{int(expiration.timestamp())}:R>",
            ephemeral=True,
        )

    @hll.command()
    async def claim(
        self,
        ctx: discord.ApplicationContext,
        hours: Option(
            int,
            "Redeem seeding hours for VIP status",
            required=False,
            min_value=1,
        ),
    ):
        """Redeem seeding hours for VIP status"""
        await ctx.defer(ephemeral=True)
        if hours is None:
            vip_value = global_config["hell_let_loose"]["seeder_vip_reward_hours"]
            message = f"{ctx.author.mention}:"
            message += f"\n💵 Use {get_command_mention(self.claim)} `$HOURS` to turn seeding hours into VIP status."
            message += (
                f"\n🚜 One hour of seeding time is `{vip_value}` hour(s) of VIP status."
            )
            message += (
                f"\nℹ️ Check your seeding hours with {get_command_mention(self.seeder)}."
            )
            await ctx.respond(message, ephemeral=True)
            return
        else:
            player = await HLL_Player.by_discord_id(ctx.author.id)
            if player is None:
                message = f"{ctx.author.mention}: Can't find your ID to claim VIP."
                message += f"\nMake sure you have run {get_command_mention(self.register)} and registered your Player ID and Discord."
                await ctx.respond(message, ephemeral=True)
                return
            else:
                player_seeding_time_hours = player.seeding_time_balance // timedelta(
                    hours=1
                )
                self.logger.debug(
                    f'User "{ctx.author.name}/{player.player_id}" is attempting to claim {hours} seeder hours from their total of {player_seeding_time_hours:,}'
                )
                if hours > player_seeding_time_hours:
                    await ctx.respond(
                        f"{ctx.author.mention}: ❌ Sorry, not enough banked time to claim `{hours}` hour(s) of VIP (Currently have `{player_seeding_time_hours:,}` banked hours).",
                        ephemeral=True,
                    )
                    return
                else:
                    # Check the previous VIP values from both RCON's to ensure they are identical prior to proceeding
                    try:
                        vip_dict = await self.client.get_vip(player.player_id)
                    except Exception:
                        await ctx.respond(
                            f"{ctx.author.mention}: There was an error fetching your current VIP status from one of the servers, try again later",
                            ephemeral=True,
                        )
                        return
                    vip_set = set(vip_dict.values())
                    if len(vip_set) != 1:
                        # VIP from all RCON's didn't match, notify.
                        await ctx.respond(
                            f"{ctx.author.mention}: It looks like your VIP status is different between servers, please contact an admin.",
                            ephemeral=True,
                        )
                        return

                    # All is well, return to the (identical) first in the list
                    vip = vip_set.pop()

                    grant_value = (
                        global_config["hell_let_loose"]["seeder_vip_reward_hours"]
                        * hours
                    )
                    if vip is None:
                        # !!! vip expiration is in utc...
                        expiration = datetime.now(timezone.utc) + timedelta(
                            hours=grant_value
                        )
                    else:
                        # Check if current expiration is in the past.  If it is, set it to current time.
                        cur_expiration = datetime.fromisoformat(vip)
                        if cur_expiration < datetime.now(timezone.utc):
                            cur_expiration = datetime.now(timezone.utc)

                        expiration = cur_expiration + timedelta(hours=grant_value)

                    message = ""
                    if expiration >= datetime(
                        year=3000, month=1, day=1, tzinfo=timezone.utc
                    ):
                        # non-expiring vip... converting seeding hours is pointless...
                        message += "Your VIP does not expire... no need to convert seeding hours!"
                    else:
                        # Make sure all RCON grants are successful.
                        result_dict = await self.client.grant_vip(
                            player.player_name, player.player_id, expiration
                        )
                        for rcon, result in result_dict.items():
                            if result is False:
                                self.logger.error(
                                    f'Problem assigning VIP in `claim` for "{rcon}": {result}'
                                )
                                await ctx.respond(
                                    f"{ctx.author.mention}: There was a problem on one of the servers assigning your VIP."
                                )
                                return

                        # !!! should only decrease banked seeding time if it is actually used...
                        player.seeding_time_balance -= timedelta(hours=hours)

                        message += f"{ctx.author.mention}: You've added `{grant_value}` hour(s) to your VIP status."
                        message += (
                            f"\nYour VIP expires <t:{int(expiration.timestamp())}:R>"
                        )

                    message += f"\nYour remaining seeder balance is `{player.seeding_time_balance // timedelta(hours=1):,}` hour(s)."
                    message += "\n💗 Thanks for seeding! 💗"
                    await player.save()
                    await ctx.respond(message, ephemeral=True)
                    return

    @hll.command()
    @guild_only()
    async def gift(
        self,
        ctx: discord.ApplicationContext,
        receiver_discord_user: Option(
            discord.Member,
            "Discord user to grant VIP hours to",
            required=True,
        ),
        hours: Option(
            int,
            "amount of hours to gift",
            required=False,
            min_value=1,
        ),
    ):
        """Gift VIP to another player"""
        await ctx.defer(ephemeral=True)
        if hours is None:
            vip_value = global_config["hell_let_loose"]["seeder_vip_reward_hours"]
            message = f"{ctx.author.mention}:"
            message += f"\n💵 Use {get_command_mention(self.gift)} `$USER` `$HOURS` to grant other players seeding hours."
            message += (
                f"\n🚜 One hour of seeding time is `{vip_value}` hour(s) of VIP status."
            )
            message += (
                f"\nℹ️ Check your seeding hours with {get_command_mention(self.seeder)}."
            )
            await ctx.respond(message, ephemeral=True)
            return
        else:
            receiver = await HLL_Player.by_discord_id(receiver_discord_user.id)
            if receiver is None:
                await ctx.respond(
                    f"No information in database for user {receiver_discord_user} ({receiver_discord_user.id}) via `player_id`. Inform them to use {get_command_mention(self.register)} to tie their ID to their discord.",
                    ephemeral=True,
                )
                return
            gifter = await HLL_Player.by_discord_id(ctx.author.id)
            if gifter is None:
                message = f"{ctx.author.mention}: Can't find your ID to claim VIP."
                message += f"\nMake sure you have run {get_command_mention(self.register)} and registered your Player ID and Discord."
                await ctx.respond(message, ephemeral=True)
                return

            gifter_seeding_time_hours = gifter.seeding_time_balance // timedelta(
                hours=1
            )
            if hours > gifter_seeding_time_hours:
                await ctx.respond(
                    f"{ctx.author.mention}: ❌ Sorry, not enough banked time to claim `{hours}` hour(s) of VIP (Currently have `{gifter_seeding_time_hours:,}` banked hours).",
                    ephemeral=True,
                )
                return
            else:
                self.logger.info(
                    f'User "{receiver}" is being gifted {hours} seeder hours by discord user {ctx.author.mention}.'
                )

                receiver.seeding_time_balance += timedelta(hours=hours)
                gifter.seeding_time_balance -= timedelta(hours=hours)

                message = ""
                message += f"{ctx.author.mention}: You've added `{hours}` hour(s) to {receiver_discord_user.mention}'s seeding bank."
                message += f"\nYour remaining seeder balance is `{gifter.seeding_time_balance // timedelta(hours=1):,}` hour(s)."
                message += "\n💗 Thanks for seeding! 💗"
                await gifter.save()
                await receiver.save()

                if ctx.channel is not None:
                    await ctx.channel.send(
                        f"{ctx.author.mention} just gifted `{hours}` hours of VIP seeding time to {receiver_discord_user.mention}!  Use {get_command_mention(self.seeder)} to check your balance."
                    )

                await ctx.respond(message, ephemeral=True)
                return

    @hll_admin.command()
    @guild_only()
    async def grant_seeder_time(
        self,
        ctx: discord.ApplicationContext,
        user: Option(
            discord.Member,
            "Discord user to grant seeder time to",
            required=True,
        ),
        hours: Option(
            int,
            "Hours of banked seeding time to grant the user",
            required=True,
        ),
    ):
        """Admin-only command to grant user banked seeding time.  The user still must redeem the time."""
        await ctx.defer(ephemeral=True)
        player = await HLL_Player.by_discord_id(user.id)
        if player is None:
            await ctx.respond(
                f"User {user} ({user.id}) ID doesn't match any known `player_id`. Inform them to use {get_command_mention(self.register)} to tie their ID to their discord.",
                ephemeral=True,
            )
            return
        self.logger.info(
            f'User "{player.discord_id}/{player.player_id}" is being granted {hours} seeder hours by discord user {ctx.author.mention}.'
        )

        old_seed_balance = player.seeding_time_balance
        player.seeding_time_balance += timedelta(hours=hours)
        await player.save()

        message = f"Successfully granted {hours} hours to seeder."
        message = f"Previous seeding balance was `{old_seed_balance}`."
        message += f"User {user}'s seeder balance is now `{player.seeding_time_balance // timedelta(hours=1):,}` hour(s)."
        await ctx.respond(message, ephemeral=True)
        return

    @hll_admin.command()
    @guild_only()
    async def check_user(
        self,
        ctx: discord.ApplicationContext,
        user: Option(
            discord.Member,
            "Discord user to get information about",
            required=True,
        ),
    ):
        "Admin-only command to check a user's VIP and seeding time."
        await ctx.defer(ephemeral=True)
        player = await HLL_Player.by_discord_id(user.id)
        if player is None:
            await ctx.respond(
                f"No information in database for user {user} ({user.id}) via `player_id`. Inform them to use {get_command_mention(self.register)} to tie their ID to their discord.",
                ephemeral=True,
            )
            return
        self.logger.debug(
            f'User {ctx.author.mention} is inspecting player data for "{player.discord_id}/{player.player_id}"'
        )

        # TODO: Merge this into a method with "grant"
        try:
            vip_dict = await self.client.get_vip(player.player_id)
        except Exception:
            await ctx.respond(
                f"{ctx.author.mention}: There was an error fetching the current VIP status for user {user}/{user.id} from one of the servers, try again later",
                ephemeral=True,
            )
            return
        vip_set = set(vip_dict.values())
        if len(vip_set) != 1:
            # VIP from all RCON's didn't match, notify.
            await ctx.respond(
                f"{ctx.author.mention}: VIP status is different between servers for user {user}/{user.id}, please contact an admin.",
                ephemeral=True,
            )
            return

        vip = vip_set.pop()

        message = f'Data for user "<@{user}>/{user.id}"'
        if vip is None:
            message += "\nVIP expiration: user has no active VIP via the RCON server."
        else:
            expiration = datetime.fromisoformat(vip)
            message += f"\nVIP expiration: <t:{int(expiration.timestamp())}:R>"
        message += f"\nDatabase player name: `{player.player_name}`"
        message += (
            f"\nLast time seeded: <t:{int(player.last_seed_check.timestamp())}:R>"
        )
        message += f"\nCurrent seeding balance (hours): `{player.seeding_time_balance // timedelta(hours=1):,}`"
        message += f"\nTotal seeding time: `{player.total_seeding_time}`"
        await ctx.respond(message, ephemeral=True)
        return

    @commands.Cog.listener()
    async def on_application_command_error(
        self, ctx: discord.ApplicationContext, error: discord.DiscordException
    ):
        """Handle exceptions and discord errors, including permissions"""

        if isinstance(error, commands.NotOwner):
            await ctx.respond(
                "Insufficient privileges to use that command.", ephemeral=True
            )
        else:
            message = global_config["seedbot"]["error_message"]
            if global_config["seedbot"]["maintainer_discord_ids"]:
                try:
                    message += (
                        "\nPlease contact the following maintainers/administrators:"
                    )
                    for maintainer in global_config["seedbot"][
                        "maintainer_discord_ids"
                    ]:
                        message += f"\n<@{maintainer}>"
                except Exception as e:
                    self.logger.error(
                        f"Failed to get maintainers from configuration: {e}"
                    )
            message += "\nThe following might help determine what the problem is:"
            message += f"\n`{error}`"
            await ctx.respond(message, ephemeral=True)
            raise error

    def cog_unload(self):
        pass


def setup(bot):
    bot.add_cog(BotCommands(bot))


def teardown(bot):
    pass
