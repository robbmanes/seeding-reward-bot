from datetime import datetime, timedelta

import discord
from discord import guild_only
from discord.commands import SlashCommandGroup, option

from seeding_reward_bot.commands.util import BotCommands
from seeding_reward_bot.main import HLLDiscordBot


class HLLAdminCommands(BotCommands):
    """
    Cog to manage hll-admin command discord interactions.
    """

    hll_admin = SlashCommandGroup("hll-admin", "Admin seeding commands")

    @hll_admin.command()
    @guild_only()
    @option("user", description="Discord user to grant seeder time to")
    @option("hours", description="Hours of banked seeding time to grant the user")
    async def grant_seeder_time(
        self, ctx: discord.ApplicationContext, user: discord.Member, hours: int
    ) -> None:
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
    @option("user", description="Discord user to get information about")
    async def check_user(
        self, ctx: discord.ApplicationContext, user: discord.Member
    ) -> None:
        """Admin-only command to check a user's VIP and seeding time."""
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


def setup(bot: HLLDiscordBot):
    bot.add_cog(HLLAdminCommands(bot))


def teardown(bot: HLLDiscordBot):
    pass
