import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import ApplicationCommandInvokeError, guild_only
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands
from tortoise.exceptions import DoesNotExist, MultipleObjectsReturned

from seeding_reward_bot.config import global_config
from seeding_reward_bot.db import HLL_Player


class EphemeralError(Exception):
    pass


class EphemeralMentionError(EphemeralError):
    pass


class EphemeralAdminError(EphemeralError):
    pass


def command_mention(cmd):
    return f"</{cmd.qualified_name}:{cmd.qualified_id}>"


class BotCommands(commands.Cog):
    """
    Cog to manage discord interactions.
    """

    hll = SlashCommandGroup("hll", "Seeding commands")
    hll_admin = SlashCommandGroup("hll-admin", "Admin seeding commands")

    def __init__(self, bot):
        self.bot = bot
        self.client = bot.client
        self.logger = logging.getLogger(__name__)

    async def get_player_by_player_id(self, player_id):
        try:
            return await HLL_Player.get(player_id=player_id)
        except MultipleObjectsReturned:
            raise EphemeralAdminError(f"Found multiple players for {player_id=}")
        except DoesNotExist:
            raise EphemeralMentionError(
                f"There is no record for that Player ID `{player_id}`; please make sure you have seeded on our servers previously and enter your Player ID (found in the top right of OPTIONS in game) to register.  Please open a ticket for additional help."
            )

    async def get_player_by_discord_id(self, discord_id, other=False):
        try:
            return await HLL_Player.get(discord_id=discord_id)
        except MultipleObjectsReturned:
            raise EphemeralAdminError(f"Multiple discord_id's found for {discord_id=}")
        except DoesNotExist:
            message = f"Discord ID <@{discord_id}> is not registered. "
            if not other:
                message += f"Use {command_mention(self.register)} to tie your Player ID to your discord."
            else:
                message += f"Inform them to use {command_mention(self.register)} to tie their Player ID to their discord."
            raise EphemeralError(message)

    async def get_vip_by_discord_id(self, discord_id, other=False):
        player = await self.get_player_by_discord_id(discord_id, other)

        # We need to ensure we get the same VIP states for both RCON's.
        try:
            vip_dict = await self.client.get_vip(player.player_id)
        except Exception:
            if other:
                raise EphemeralMentionError(
                    f"There was an error fetching the current VIP status for user <@{discord_id}> from one of the servers, try again later"
                )
            raise EphemeralMentionError(
                "There was an error fetching your current VIP status from one of the servers, try again later"
            )

        vip_set = set(vip_dict.values())
        if len(vip_set) != 1:
            # VIP from all RCON's didn't match, notify.
            raise EphemeralAdminError(
                f"VIP status is different between servers for {player.player_id=}"
            )

        # All is well, return to the (identical) first in the list
        return vip_set.pop(), player

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

        player = await self.get_player_by_player_id(player_id)

        if player.discord_id == ctx.author.id:
            raise EphemeralError("That `player_id` is already registered to you!")
        elif player.discord_id:
            self.logger.debug(
                f"Discord user {ctx.author.name}/{ctx.author.id} attempted to register player_id `{player_id}` but it is already owned by Discord user {player.discord_id}"
            )
            raise EphemeralError(
                "That `player_id` is already registered to someone else."
            )

        player.discord_id = ctx.author.id
        await player.save()
        self.logger.debug(
            f"Updated user {ctx.author.name}/{ctx.author.id} with player_id `{player_id}`"
        )
        await ctx.respond(
            f"{ctx.author.mention}: I've registered your `player_id` to your Discord account. Thanks!",
            ephemeral=True,
        )

    @hll.command()
    async def seeder(self, ctx: discord.ApplicationContext):
        """Check your seeding statistics"""

        await ctx.defer(ephemeral=True)

        player = await self.get_player_by_discord_id(ctx.author.id)

        message = (
            f"Seeding stats for {ctx.author.mention}:",
            f" 🌱 Total seeding time (hours): `{player.total_seeding_time}`",
            f" 🏦 Unspent seeding time balance (hours): `{player.seeding_time_balance // timedelta(hours=1):,}`",
            f" 🕰️ Last seeding time: <t:{int(player.last_seed_check.timestamp())}:R>",
            f" ℹ️ Turn your seeding hours into VIP time with {command_mention(self.claim)}. One hour of seeding = {global_config['hell_let_loose']['seeder_vip_reward_hours']} hour(s) of VIP.",
        )
        await ctx.respond("\n".join(message), ephemeral=True)

    @hll.command()
    async def vip(self, ctx: discord.ApplicationContext):
        """Check your VIP status"""

        await ctx.defer(ephemeral=True)

        self.logger.debug(f"VIP query for `{ctx.author.id}/{ctx.author.name}`.")

        vip, _ = await self.get_vip_by_discord_id(ctx.author.id)

        if vip is None:
            message = f"No VIP record found for {ctx.author.mention}."
        else:
            expiration = datetime.fromisoformat(vip)
            message = f"{ctx.author.mention}: your VIP "
            if expiration < datetime.now(timezone.utc):
                message += "appears to have expired."
            elif expiration >= datetime(year=3000, month=1, day=1, tzinfo=timezone.utc):
                # crcon uses UTC 3000-01-01 for indefinite VIP
                #   and checks with >= to test for indefinite
                # converting seeding hours is pointless in this case.
                message += "does not expire!"
            else:
                # https://discord.com/developers/docs/reference#message-formatting-formats
                message += f"expires <t:{int(expiration.timestamp())}:R>"

        await ctx.respond(message, ephemeral=True)

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
            message = (
                f"{ctx.author.mention}:",
                f"💵 Use {command_mention(self.claim)} `$HOURS` to turn seeding hours into VIP status.",
                f"🚜 One hour of seeding time is `{global_config['hell_let_loose']['seeder_vip_reward_hours']}` hour(s) of VIP status.",
                f"ℹ️ Check your seeding hours with {command_mention(self.seeder)}.",
            )
            raise EphemeralError("\n".join(message))

        vip, player = await self.get_vip_by_discord_id(ctx.author.id)

        player_seeding_time_hours = player.seeding_time_balance // timedelta(hours=1)
        self.logger.debug(
            f'User "{ctx.author.name}/{player.player_id}" is attempting to claim {hours} seeder hours from their total of {player_seeding_time_hours:,}'
        )
        if hours > player_seeding_time_hours:
            raise EphemeralError(
                f"{ctx.author.mention}: ❌ Sorry, not enough banked time to claim `{hours}` hour(s) of VIP (Currently have `{player_seeding_time_hours:,}` banked hours)."
            )

        grant_value = global_config["hell_let_loose"]["seeder_vip_reward_hours"] * hours
        if vip is None:
            # !!! vip expiration is in utc...
            expiration = datetime.now(timezone.utc) + timedelta(hours=grant_value)
        else:
            # Check if current expiration is in the past.  If it is, set it to current time.
            cur_expiration = datetime.fromisoformat(vip)
            if cur_expiration < datetime.now(timezone.utc):
                cur_expiration = datetime.now(timezone.utc)

            expiration = cur_expiration + timedelta(hours=grant_value)

        if expiration >= datetime(year=3000, month=1, day=1, tzinfo=timezone.utc):
            # non-expiring vip... converting seeding hours is pointless...
            message = ("Your VIP does not expire... no need to convert seeding hours!",)

        else:
            # Make sure all RCON grants are successful.
            result_dict = await self.client.grant_vip(
                player.player_name, player.player_id, expiration
            )
            for rcon, result in result_dict.items():
                if result is False:
                    raise EphemeralError(
                        f"{ctx.author.mention}: There was a problem on one of the servers assigning your VIP."
                    )

            # !!! should only decrease banked seeding time if it is actually used...
            player.seeding_time_balance -= timedelta(hours=hours)

            message = (
                f"{ctx.author.mention}: You've added `{grant_value}` hour(s) to your VIP status.",
                f"Your VIP expires <t:{int(expiration.timestamp())}:R>",
            )

        message += (
            f"Your remaining seeder balance is `{player.seeding_time_balance // timedelta(hours=1):,}` hour(s).",
            "💗 Thanks for seeding! 💗",
        )
        await player.save()
        await ctx.respond("\n".join(message), ephemeral=True)

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
            message = (
                f"{ctx.author.mention}:",
                f"💵 Use {command_mention(self.gift)} `$USER` `$HOURS` to grant other players seeding hours.",
                f"🚜 One hour of seeding time is `{global_config['hell_let_loose']['seeder_vip_reward_hours']}` hour(s) of VIP status.",
                f"ℹ️ Check your seeding hours with {command_mention(self.seeder)}.",
            )
            raise EphemeralError("\n".join(message))

        if receiver_discord_user == ctx.author:
            raise EphemeralMentionError("You can't gift to yourself.")

        receiver = await self.get_player_by_discord_id(receiver_discord_user.id, True)
        gifter = await self.get_player_by_discord_id(ctx.author.id)

        gifter_seeding_time_hours = gifter.seeding_time_balance // timedelta(hours=1)
        if hours > gifter_seeding_time_hours:
            raise EphemeralError(
                f"{ctx.author.mention}: ❌ Sorry, not enough banked time to claim `{hours}` hour(s) of VIP (Currently have `{gifter_seeding_time_hours:,}` banked hours)."
            )

        self.logger.info(
            f'User "{receiver}" is being gifted {hours} seeder hours by discord user {ctx.author.mention}.'
        )

        receiver.seeding_time_balance += timedelta(hours=hours)
        gifter.seeding_time_balance -= timedelta(hours=hours)

        message = (
            f"{ctx.author.mention}: You've added `{hours}` hour(s) to {receiver_discord_user.mention}'s seeding bank.",
            f"Your remaining seeder balance is `{gifter.seeding_time_balance // timedelta(hours=1):,}` hour(s).",
            "💗 Thanks for seeding! 💗",
        )
        await gifter.save()
        await receiver.save()

        await ctx.channel.send(
            f"{ctx.author.mention} just gifted `{hours}` hours of VIP seeding time to {receiver_discord_user.mention}!  Use {command_mention(self.seeder)} to check your balance."
        )

        await ctx.respond("\n".join(message), ephemeral=True)

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
        player = await self.get_player_by_discord_id(user.id, True)
        self.logger.info(
            f'User "{player.discord_id}/{player.player_id}" is being granted {hours} seeder hours by discord user {ctx.author.mention}.'
        )

        old_seed_balance = player.seeding_time_balance
        player.seeding_time_balance += timedelta(hours=hours)
        await player.save()

        message = (
            f"Successfully granted `{hours}` hour(s) to seeder {user.mention}",
            f"Previous seeding balance was `{old_seed_balance}`.",
            f"User {user.mention}'s seeder balance is now `{player.seeding_time_balance // timedelta(hours=1):,}` hour(s).",
        )
        await ctx.respond("\n".join(message), ephemeral=True)

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

        vip, player = await self.get_vip_by_discord_id(user.id, True)

        self.logger.debug(
            f'User {ctx.author.mention} is inspecting player data for "{player.discord_id}/{player.player_id}"'
        )

        message = (f'Data for user "{user.mention}/{user.id}"',)
        if vip is None:
            message += ("VIP expiration: user has no active VIP via the RCON server.",)
        else:
            expiration = datetime.fromisoformat(vip)
            message += (f"VIP expiration: <t:{int(expiration.timestamp())}:R>",)
        message += (
            f"Database player name: `{player.player_name}`",
            f"Last time seeded: <t:{int(player.last_seed_check.timestamp())}:R>",
            f"Current seeding balance (hours): `{player.seeding_time_balance // timedelta(hours=1):,}`",
            f"Total seeding time: `{player.total_seeding_time}`",
        )
        await ctx.respond("\n".join(message), ephemeral=True)

    async def maintainer_error_message(self, ctx, error):
        message = (global_config["seedbot"]["error_message"],)
        if global_config["seedbot"]["maintainer_discord_ids"]:
            message += ("Please contact the following maintainers/administrators:",)
            try:
                for maintainer in global_config["seedbot"]["maintainer_discord_ids"]:
                    message += (f"<@{maintainer}>",)
            except Exception as exc:
                self.logger.error(
                    "Failed to get maintainers from configuration", exc_info=exc
                )
        message += (
            "The following might help determine what the problem is:",
            f"`{error}`",
        )
        await ctx.respond("\n".join(message), ephemeral=True)

    async def cog_command_error(
        self, ctx: discord.ApplicationContext, error: discord.DiscordException
    ):
        """Handle exceptions and discord errors, including permissions"""
        if isinstance(error, ApplicationCommandInvokeError):
            error = error.original

        if isinstance(error, commands.NotOwner):
            await ctx.respond(
                "Insufficient privileges to use that command.", ephemeral=True
            )
        elif isinstance(error, EphemeralAdminError):
            self.logger.error("An error occured", exc_info=error)
            await self.maintainer_error_message(ctx, error)
        elif isinstance(error, EphemeralError):
            message = error
            if isinstance(error, EphemeralMentionError):
                message = f"{ctx.author.mention}: {message}"
            await ctx.respond(message, ephemeral=True)
        else:
            self.logger.error("An unexpected error occured", exc_info=error)
            await self.maintainer_error_message(ctx, error)

    def cog_unload(self):
        pass


def setup(bot):
    bot.add_cog(BotCommands(bot))


def teardown(bot):
    pass
