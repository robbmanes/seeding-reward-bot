import zoneinfo
from datetime import datetime, timedelta, timezone

import discord
from discord import guild_only
from discord.commands import SlashCommandGroup, option
from tortoise.expressions import F
from tortoise.functions import Count
from tortoise.transactions import atomic

from seeding_reward_bot.commands.util import (
    BotCommands,
    DateTrunc,
    EphemeralError,
    EphemeralMentionError,
    Greatest,
    Least,
    RankOrderByDesc,
    SumTypeChange,
    add_embed_table,
    command_mention,
    parse_datetime,
)
from seeding_reward_bot.config import global_config
from seeding_reward_bot.db import Seeding_Session
from seeding_reward_bot.main import HLLDiscordBot


class HLLCommands(BotCommands):
    """
    Cog to manage hll command discord interactions.
    """

    hll = SlashCommandGroup("hll", "Seeding commands")
    hll_leaderboard = hll.create_subgroup(
        "leaderboard", "Seeding leaderboard and stats"
    )

    def hours_help_msg(
        self,
        ctx: discord.ApplicationContext,
        cmd: discord.ApplicationCommand,
        cmd_help: str,
    ) -> str:
        message = (
            f"{ctx.author.mention}:",
            f"💵 Use {command_mention(cmd)} {cmd_help}",
            f"🚜 One hour of seeding time is `{global_config.seeder_vip_reward_hours}` hour(s) of VIP status.",
            f"ℹ️ Check your seeding hours with {command_mention(self.seeder)}.",
        )
        return "\n".join(message)

    @hll.command()
    async def help(self, ctx: discord.ApplicationContext) -> None:
        """Get help about commands and their use"""
        embed = discord.Embed.from_dict(dict(global_config.help_embed))

        message = (
            f"- {command_mention(self.help)} - Show this help.",
            f"- {command_mention(self.register)} `Player ID` - Will register your Player ID with the bot.  This is so you are able to track and redeem seeding time via discord.",
            f"- {command_mention(self.seeder)} - See your general time seeding, and how many unclaimed hours you have.",
            f"- {command_mention(self.claim)} `Hours` - Redeem your seeding time.  One hour of seeding time is `{global_config.seeder_vip_reward_hours}` hour(s) of VIP, starting the moment you claim it.",
            f"- {command_mention(self.vip)} - Check your current seeding VIP status on the servers.",
        )
        message = "\n".join(message)

        if embed.description:
            embed.description += f"\n{message}"
        else:
            embed.description = message

        await ctx.respond(embed=embed)

    @hll.command()
    @option(
        "player_id",
        description="Your Player ID (for Steam your SteamID64) found in the top right of OPTIONS in game",
    )
    async def register(self, ctx: discord.ApplicationContext, player_id: str) -> None:
        """Register your discord account to your Player ID"""
        await ctx.defer(ephemeral=True)

        await self.register_player(ctx, player_id, ctx.author)

        await ctx.respond(
            f"{ctx.author.mention}: I've registered your `player_id` to your Discord account. Thanks!",
            ephemeral=True,
        )

    @hll.command()
    async def seeder(self, ctx: discord.ApplicationContext) -> None:
        """Check your seeding statistics"""
        await ctx.defer(ephemeral=True)

        player = await self.get_player_by_discord_id(ctx.author.id)

        message = (
            f"Seeding stats for {ctx.author.mention}:",
            f" 🌱 Total seeding time (hours): `{player.total_seeding_time}`",
            f" 🏦 Unspent seeding time balance (hours): `{player.seeding_time_balance // timedelta(hours=1):,}`",
            f" 🕰️ Last seeding time: <t:{int(player.last_seed_check.timestamp())}:R>",
            f" ℹ️ Turn your seeding hours into VIP time with {command_mention(self.claim)}. One hour of seeding = {global_config.seeder_vip_reward_hours} hour(s) of VIP.",
        )
        await ctx.respond("\n".join(message), ephemeral=True)

    @hll.command()
    async def vip(self, ctx: discord.ApplicationContext) -> None:
        """Check your VIP status"""
        await ctx.defer(ephemeral=True)

        self.logger.debug(f"VIP query for `{ctx.author.id}/{ctx.author.name}`.")

        player = await self.get_player_by_discord_id(ctx.author.id)
        vip = await self.get_vip_by_player_id(player.player_id)

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
    @option(
        "hours",
        input_type=int,
        description=f"Seeding hours to claim, at a conversion of one seeding hour = {global_config.seeder_vip_reward_hours} hour(s) of VIP",
        min_value=1,
    )
    @atomic()
    async def claim(
        self, ctx: discord.ApplicationContext, hours: int | None = None
    ) -> None:
        """Redeem seeding hours for VIP status"""
        await ctx.defer(ephemeral=True)

        if hours is None:
            message = self.hours_help_msg(
                ctx, self.claim, "`$HOURS` to turn seeding hours into VIP status."
            )
            raise EphemeralError(message)

        player = await self.get_player_by_discord_id(ctx.author.id, update=True)
        vip = await self.get_vip_by_player_id(player.player_id)

        player_seeding_time_hours = player.seeding_time_balance // timedelta(hours=1)
        self.logger.debug(
            f'User "{ctx.author.name}/{player.player_id}" is attempting to claim {hours} seeder hours from their total of {player_seeding_time_hours:,}'
        )
        if hours > player_seeding_time_hours:
            raise EphemeralMentionError(
                f"❌ Sorry, not enough banked time to claim `{hours}` hour(s) of VIP (Currently have `{player_seeding_time_hours:,}` banked hours)."
            )

        grant_value = global_config.seeder_vip_reward_hours * hours
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
            if not all(result_dict.values()):
                raise EphemeralMentionError(
                    "There was a problem on one of the servers assigning your VIP."
                )

            # !!! should only decrease banked seeding time if it is actually used...
            player.seeding_time_balance -= timedelta(hours=hours)

            message = (
                f"{ctx.author.mention}: You've added `{grant_value}` hour(s) to your VIP status.",
                f"Your VIP expires <t:{int(expiration.timestamp())}:R>",
            )
            await player.save(update_fields=["seeding_time_balance"])

        message += (
            f"Your remaining seeder balance is `{player.seeding_time_balance // timedelta(hours=1):,}` hour(s).",
            "💗 Thanks for seeding! 💗",
        )
        await ctx.respond("\n".join(message), ephemeral=True)

    @hll.command()
    @guild_only()
    @option("receiver_discord_user", description="Discord user to grant VIP hours to")
    @option(
        "hours",
        input_type=int,
        description="Amount of seeding hours to gift",
        required=False,
        min_value=1,
    )
    @atomic()
    async def gift(
        self,
        ctx: discord.ApplicationContext,
        receiver_discord_user: discord.Member,
        hours: int | None,
    ) -> None:
        """Gift VIP to another player"""
        await ctx.defer(ephemeral=True)

        if hours is None:
            message = self.hours_help_msg(
                ctx, self.gift, "`$USER` `$HOURS` to grant other players seeding hours."
            )
            raise EphemeralError(message)

        if receiver_discord_user == ctx.author:
            raise EphemeralMentionError("You can't gift to yourself.")

        receiver = await self.get_player_by_discord_id(
            receiver_discord_user.id, update=True, other=True
        )
        gifter = await self.get_player_by_discord_id(ctx.author.id, update=True)

        gifter_seeding_time_hours = gifter.seeding_time_balance // timedelta(hours=1)
        if hours > gifter_seeding_time_hours:
            raise EphemeralMentionError(
                f"❌ Sorry, not enough banked time to claim `{hours}` hour(s) of VIP (Currently have `{gifter_seeding_time_hours:,}` banked hours)."
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
        await gifter.save(update_fields=["seeding_time_balance"])
        await receiver.save(update_fields=["seeding_time_balance"])

        await ctx.send(
            f"{ctx.author.mention} just gifted `{hours}` hours of VIP seeding time to {receiver_discord_user.mention}!  Use {command_mention(self.seeder)} to check your balance."
        )

        await ctx.respond("\n".join(message), ephemeral=True)

    @hll_leaderboard.command()
    @option(
        "period",
        description="Which leaderboard period to show",
        choices=["weekly", "monthly", "yearly"],
    )
    @option(
        "reference",
        description="What date to use as the reference of the shown leaderboard period",
    )
    @option(
        "timezone",
        description="What timezone to use",
        autocomplete=discord.utils.basic_autocomplete(zoneinfo.available_timezones()),
    )
    async def show(
        self,
        ctx: discord.ApplicationContext,
        period: str = "weekly",
        reference: str = "now",
        timezone: str = global_config.leaderboard_default_timezone,
    ) -> None:
        """Show the period leaderboard for seeding time"""

        tzinfo = zoneinfo.ZoneInfo(timezone)
        ref_datetime = parse_datetime(reference, timezone)

        match period:
            case "weekly":
                start = datetime(
                    ref_datetime.year,
                    ref_datetime.month,
                    ref_datetime.day,
                    tzinfo=tzinfo,
                ) - timedelta(days=ref_datetime.weekday())
                end = start + timedelta(weeks=1)
            case "monthly":
                start = datetime(
                    ref_datetime.year,
                    ref_datetime.month,
                    1,
                    tzinfo=tzinfo,
                )
                if ref_datetime.month == 12:
                    end = start.replace(year=ref_datetime.year + 1, month=1)
                else:
                    end = start.replace(month=ref_datetime.month + 1)
            case "yearly":
                start = datetime(
                    ref_datetime.year,
                    1,
                    1,
                    tzinfo=tzinfo,
                )
                end = start.replace(year=ref_datetime.year + 1)

        await self._leaderboard(
            ctx,
            start,
            end,
            f"{period.capitalize()} Seeding Leaderboard",
        )

    @hll_leaderboard.command()
    @option(
        "start",
        description="Start date and time to show the leaderboard for",
    )
    @option(
        "end",
        description="End date and time to show the leaderboard for",
    )
    async def show_range(
        self,
        ctx: discord.ApplicationContext,
        start: str,
        end: str,
    ) -> None:
        """Show the range leaderboard for seeding time"""

        await self._leaderboard(
            ctx,
            parse_datetime(start, global_config.leaderboard_default_timezone),
            parse_datetime(end, global_config.leaderboard_default_timezone),
            "Seeding Leaderboard",
        )

    async def _leaderboard(
        self,
        ctx: discord.ApplicationContext,
        start: datetime,
        end: datetime,
        title: str,
    ) -> None:
        await ctx.defer()

        columns = {
            "Rank": "rank",
            "Player Name": "hll_player__player_name",
            "Sessions": "sessions",
            "duration": "duration",
        }

        seeding_session = Seeding_Session.filter(
            end_time__gte=start,
            hll_player__hidden=False,
        )
        if end < datetime.now(timezone.utc):
            seeding_session = seeding_session.filter(start_time__lt=end)
            end_func = Least("end_time", end)
        else:
            end_func = F("end_time")
        duration = SumTypeChange(end_func - Greatest("start_time", start))

        rows = (
            await seeding_session.annotate(
                duration=DateTrunc(duration, "second"),
                sessions=Count("hll_player_id"),
                rank=RankOrderByDesc(duration),
            )
            .group_by("hll_player_id", "hll_player__player_name")
            .order_by("rank")
            .limit(20)
            .values_list(*columns.values())
        )
        embed = discord.Embed(
            title=title,
            description=f"Starting at <t:{int(start.timestamp())}:s>",
            timestamp=end,
            footer=discord.EmbedFooter("Until"),
        )
        embed = add_embed_table(
            embed,
            headers=columns.keys(),
            data=rows,
            fmt="{}. [{}][{}]: {}",
        )

        await ctx.respond(embed=embed)


def setup(bot: HLLDiscordBot):
    bot.add_cog(HLLCommands(bot))


def teardown(bot: HLLDiscordBot):
    pass
