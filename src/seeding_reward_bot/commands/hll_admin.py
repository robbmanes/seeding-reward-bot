from datetime import datetime, timedelta

import discord
from discord import guild_only
from discord.commands import SlashCommandGroup, option
from tortoise.transactions import atomic

from seeding_reward_bot.commands.util import (
    BotCommands,
    get_embed_table,
)
from seeding_reward_bot.db import HLL_Player
from seeding_reward_bot.main import HLLDiscordBot


class HLLAdminCommands(BotCommands):
    """
    Cog to manage hll-admin command discord interactions.
    """

    hll_admin = SlashCommandGroup("hll-admin", "Admin seeding commands")
    hll_admin_leaderboard = hll_admin.create_subgroup(
        "leaderboard", "Admin leaderboard commands"
    )

    @hll_admin.command()
    @guild_only()
    @option("user", description="Discord user to grant seeder time to")
    @option("hours", description="Hours of banked seeding time to grant the user")
    @atomic()
    async def grant_seeder_time(
        self, ctx: discord.ApplicationContext, user: discord.Member, hours: int
    ) -> None:
        """Admin-only command to grant user banked seeding time.  The user still must redeem the time."""
        await ctx.defer(ephemeral=True)
        player = await self.get_player_by_discord_id(user.id, other=True, update=True)
        self.logger.info(
            f'User "{player.discord_id}/{player.player_id}" is being granted {hours} seeder hours by discord user {ctx.author.mention}.'
        )

        old_seed_balance = player.seeding_time_balance
        player.seeding_time_balance += timedelta(hours=hours)
        await player.save(update_fields=["seeding_time_balance"])

        message = (
            f"Successfully granted `{hours}` hour(s) to seeder {user.mention}",
            f"Previous seeding balance was `{old_seed_balance}`.",
            f"User {user.mention}'s seeder balance is now `{player.seeding_time_balance // timedelta(hours=1):,}` hour(s).",
        )
        await ctx.respond("\n".join(message), ephemeral=True)

    hll_admin_check = hll_admin.create_subgroup(
        "check", "Admin-only commands to check VIP and seeding time."
    )

    @hll_admin_check.command(name="discord")
    @guild_only()
    @option("user", description="Discord user to get information about")
    async def check_discord(
        self, ctx: discord.ApplicationContext, user: discord.Member
    ) -> None:
        """Admin-only command to check a Discord user's VIP and seeding time."""
        await ctx.defer(ephemeral=True)
        player = await self.get_player_by_discord_id(user.id, other=True)
        await self._check(ctx, player)

    @hll_admin_check.command(name="player")
    @guild_only()
    @option("player_id", description="Player ID to get information about")
    async def check_player(
        self, ctx: discord.ApplicationContext, player_id: str
    ) -> None:
        """Admin-only command to check a player's VIP and seeding time."""
        await ctx.defer(ephemeral=True)
        player = await self.get_player_by_player_id(player_id, other=True)
        await self._check(ctx, player)

    async def _check(self, ctx: discord.ApplicationContext, player: HLL_Player) -> None:
        vip = await self.get_vip_by_player_id(player.player_id, other=True)

        self.logger.debug(
            f'User {ctx.author.mention} is inspecting player data for "{player.discord_id}/{player.player_id}"'
        )

        message = (f'Data for user "<@{player.discord_id}>/{player.discord_id}"',)
        if vip is None:
            message += ("VIP expiration: user has no active VIP via the RCON server.",)
        else:
            expiration = datetime.fromisoformat(vip)
            message += (f"VIP expiration: <t:{int(expiration.timestamp())}:R>",)
        message += (
            f"Database player name: `{player.player_name}`",
            f"Database player ID: `{player.player_id}`",
            f"Last time seeded: <t:{int(player.last_seed_check.timestamp())}:R>",
            f"Current seeding balance (hours): `{player.seeding_time_balance // timedelta(hours=1):,}`",
            f"Total seeding time: `{player.total_seeding_time}`",
        )
        await ctx.respond("\n".join(message), ephemeral=True)

    @hll_admin.command()
    @option("user", description="Discord user to register")
    @option(
        "player_id",
        description="Player ID to register",
    )
    async def register(
        self, ctx: discord.ApplicationContext, user: discord.Member, player_id: str
    ) -> None:
        """Admin-only command to register a discord account to a Player ID"""
        await ctx.defer(ephemeral=True)

        await self.register_player(ctx, player_id, user, other=True)

        await ctx.respond(
            f"Registered `{player_id=}` to Discord account {user.mention}/{user.id}",
            ephemeral=True,
        )

    @hll_admin.command()
    @guild_only()
    @option("user", description="Discord user to unregister")
    @atomic()
    async def unregister(
        self, ctx: discord.ApplicationContext, user: discord.Member
    ) -> None:
        """Admin-only command to unregister a discord account from a Player ID."""
        await ctx.defer(ephemeral=True)
        player = await self.get_player_by_discord_id(user.id, other=True, update=True)
        self.logger.debug(
            f'User {ctx.author.mention} is unregistering "{player.discord_id}/{player.player_id}"'
        )

        player.discord_id = None  # type: ignore[invalid-assignment]
        await player.save(update_fields=["discord_id"])

        message = (
            f"Successfully unregistered {user.mention}",
            f"Player name was: `{player.player_name}`",
            f"Player ID was: `{player.player_id}`",
        )
        await ctx.respond("\n".join(message), ephemeral=True)

    _hide_unhide_pid_option = option(
        "player_id",
        description="Player ID found in the top right of OPTIONS in game",
    )

    @hll_admin_leaderboard.command()
    @guild_only()
    @_hide_unhide_pid_option
    async def hide_player(
        self, ctx: discord.ApplicationContext, player_id: str
    ) -> None:
        """Admin-only command to hide a Player ID from being shown in seeding leaderboards"""
        await self._hide_player(ctx, player_id)

    @hll_admin_leaderboard.command()
    @guild_only()
    @_hide_unhide_pid_option
    async def unhide_player(
        self, ctx: discord.ApplicationContext, player_id: str
    ) -> None:
        """Admin-only command to unhide a Player ID from being shown in seeding leaderboards"""
        await self._hide_player(ctx, player_id, False)

    @atomic()
    async def _hide_player(self, ctx, player_id, hide=True) -> None:
        await ctx.defer(ephemeral=True)

        player = await self.get_player_by_player_id(player_id, other=True, update=True)
        message = f"{player} ({player_id}) was "
        if player.hidden != hide:
            player.hidden = hide
            await player.save(update_fields=["hidden"])
        else:
            message += "already "

        message += "hidden" if hide else "unhidden"
        await ctx.respond(message, ephemeral=True)

    @hll_admin_leaderboard.command()
    @guild_only()
    async def show_hidden_players(self, ctx: discord.ApplicationContext) -> None:
        """Admin-only command to display the players hidden from the seeding leaderboards"""
        await ctx.defer(ephemeral=True)

        columns = {
            "Player Name": "player_name",
            "Player ID": "player_id",
        }
        players = await HLL_Player.filter(hidden=True).values_list(*columns.values())
        embed = get_embed_table(
            "Players Hidden from Seeding Leaderboard",
            columns.keys(),
            players,
            "{} ({})",
        )

        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot: HLLDiscordBot):
    bot.add_cog(HLLAdminCommands(bot))


def teardown(bot: HLLDiscordBot):
    pass
