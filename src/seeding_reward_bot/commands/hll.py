from datetime import datetime, timedelta, timezone

import discord
from discord import guild_only
from discord.commands import SlashCommandGroup, option

from seeding_reward_bot.commands.util import (
    BotCommands,
    EphemeralError,
    EphemeralMentionError,
    command_mention,
)
from seeding_reward_bot.config import global_config
from seeding_reward_bot.main import HLLDiscordBot


class HLLCommands(BotCommands):
    """
    Cog to manage hll command discord interactions.
    """

    hll = SlashCommandGroup("hll", "Seeding commands")

    def hours_help_msg(
        self,
        ctx: discord.ApplicationContext,
        cmd: discord.ApplicationCommand,
        cmd_help: str,
    ) -> str:
        message = (
            f"{ctx.author.mention}:",
            f"💵 Use {command_mention(cmd)} {cmd_help}",
            f"🚜 One hour of seeding time is `{global_config['hell_let_loose']['seeder_vip_reward_hours']}` hour(s) of VIP status.",
            f"ℹ️ Check your seeding hours with {command_mention(self.seeder)}.",
        )
        return "\n".join(message)

    @hll.command()
    @option(
        "player_id",
        description="Your Player ID (for Steam your SteamID64) found in the top right of OPTIONS in game",
    )
    async def register(self, ctx: discord.ApplicationContext, player_id: str) -> None:
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
    async def seeder(self, ctx: discord.ApplicationContext) -> None:
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
    async def vip(self, ctx: discord.ApplicationContext) -> None:
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
    @option(
        "hours",
        input_type=int,
        description=f"Seeding hours to claim, at a conversion of one seeding hour = {global_config['hell_let_loose']['seeder_vip_reward_hours']} hour(s) of VIP",
        required=False,
        min_value=1,
    )
    async def claim(self, ctx: discord.ApplicationContext, hours: int | None) -> None:
        """Redeem seeding hours for VIP status"""
        await ctx.defer(ephemeral=True)

        if hours is None:
            message = self.hours_help_msg(
                ctx, self.claim, "`$HOURS` to turn seeding hours into VIP status."
            )
            raise EphemeralError(message)

        vip, player = await self.get_vip_by_discord_id(ctx.author.id)

        player_seeding_time_hours = player.seeding_time_balance // timedelta(hours=1)
        self.logger.debug(
            f'User "{ctx.author.name}/{player.player_id}" is attempting to claim {hours} seeder hours from their total of {player_seeding_time_hours:,}'
        )
        if hours > player_seeding_time_hours:
            raise EphemeralMentionError(
                f"❌ Sorry, not enough banked time to claim `{hours}` hour(s) of VIP (Currently have `{player_seeding_time_hours:,}` banked hours)."
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

        message += (
            f"Your remaining seeder balance is `{player.seeding_time_balance // timedelta(hours=1):,}` hour(s).",
            "💗 Thanks for seeding! 💗",
        )
        await player.save()
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

        receiver = await self.get_player_by_discord_id(receiver_discord_user.id, True)
        gifter = await self.get_player_by_discord_id(ctx.author.id)

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
        await gifter.save()
        await receiver.save()

        await ctx.channel.send(
            f"{ctx.author.mention} just gifted `{hours}` hours of VIP seeding time to {receiver_discord_user.mention}!  Use {command_mention(self.seeder)} to check your balance."
        )

        await ctx.respond("\n".join(message), ephemeral=True)


def setup(bot: HLLDiscordBot):
    bot.add_cog(HLLCommands(bot))


def teardown(bot: HLLDiscordBot):
    pass
