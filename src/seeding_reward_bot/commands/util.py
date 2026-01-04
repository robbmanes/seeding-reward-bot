import logging

import discord
from discord import ApplicationCommandInvokeError
from discord.ext import commands
from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.transactions import atomic

from seeding_reward_bot.config import global_config
from seeding_reward_bot.db import HLL_Player
from seeding_reward_bot.main import HLLDiscordBot


class EphemeralError(Exception):
    pass


class EphemeralMentionError(EphemeralError):
    pass


class EphemeralAdminError(EphemeralError):
    pass


def command_mention(cmd: discord.ApplicationCommand | None):
    if cmd:
        return f"</{cmd.qualified_name}:{cmd.qualified_id}>"
    return "`cmd unknown`"


class BotCommands(commands.Cog):
    """
    Cog to manage base discord interactions.
    """

    def __init__(self, bot: HLLDiscordBot):
        self.bot = bot
        self.client = bot.client
        self.logger = logging.getLogger(__name__)

    @staticmethod
    async def get_player_by_player_id(
        player_id: str, *, other: bool = False
    ) -> HLL_Player:
        try:
            return await HLL_Player.select_for_update().get(player_id=player_id)
        except DoesNotExist:
            message = f"There is no record for that Player ID `{player_id}`"
            if not other:
                message += "; please make sure you have seeded on our servers previously and enter your Player ID (found in the top right of OPTIONS in game) to register.  Please open a ticket for additional help."
            raise EphemeralMentionError(message)

    async def get_player_by_discord_id(
        self, discord_id: int, *, other: bool = False, update: bool = False
    ) -> HLL_Player:
        try:
            hll_player = HLL_Player
            if update:
                hll_player = hll_player.select_for_update()
            return await hll_player.get(discord_id=discord_id)
        except DoesNotExist:
            message = f"Discord ID <@{discord_id}> is not registered. "
            register_cmd = command_mention(
                self.bot.get_application_command("hll register")
            )
            if not other:
                message += f"Use {register_cmd} to tie your Player ID to your discord."
            else:
                message += f"Inform them to use {register_cmd} to tie their Player ID to their discord."
            raise EphemeralError(message)

    async def get_vip_by_player_id(self, player_id: str, *, other: bool = False) -> str:
        # We need to ensure we get the same VIP states for both RCON's.
        try:
            vip_dict = await self.client.get_vip(player_id)
        except Exception:
            message = "There was an error fetching "
            if other:
                message += f"the current VIP status for player ({player_id})"
            else:
                message += "your current VIP status"
            message += " from one of the servers, try again later"
            raise EphemeralMentionError(message)

        vip_set = set(vip_dict.values())
        if len(vip_set) != 1:
            # VIP from all RCON's didn't match, notify.
            raise EphemeralAdminError(
                f"VIP status is different between servers for {player_id=}"
            )

        # All is well, return to the (identical) first in the list
        return vip_set.pop()

    @atomic()
    async def register_player(
        self,
        ctx: discord.ApplicationContext,
        player_id: str,
        discord_user: discord.Member,
        *,
        other: bool = False,
    ) -> None:
        player = await self.get_player_by_player_id(player_id)

        if player.discord_id:
            message = "That `player_id` is already registered to "
            if other:
                message += f"<@{player.discord_id}>/{player.discord_id}"
            elif player.discord_id == discord_user.id:
                message += "you!"
            else:
                message += "someone else."
            self.logger.debug(
                f"Discord user {ctx.author.name}/{ctx.author.id} attempted to register player_id `{player_id}` to {discord_user.name}/{discord_user.id} but it is already owned by Discord user {player.discord_id}"
            )
            raise EphemeralError(message)

        player.discord_id = discord_user.id
        try:
            await player.save(update_fields=["discord_id"])
        except IntegrityError:
            if other:
                message = f"{discord_user.mention}/{discord_user.id} looks to be registered already"
            else:
                message = "It looks like your Discord user is already registered to a player_id"
            self.logger.exception(
                f"{discord_user.name=}/{discord_user.id=} already registered?"
            )
            raise EphemeralError(message)

        self.logger.debug(
            f"Updated user {discord_user.name}/{discord_user.id} with player_id `{player_id}`"
        )

    async def maintainer_error_message(
        self, ctx: discord.ApplicationContext, error: Exception
    ) -> None:
        message = (global_config["seedbot"]["error_message"],)
        if global_config["seedbot"]["maintainer_discord_ids"]:
            message += ("Please contact the following maintainers/administrators:",)
            try:
                for maintainer in global_config["seedbot"]["maintainer_discord_ids"]:
                    message += (f"<@{maintainer}>",)
            except Exception:
                self.logger.exception("Failed to get maintainers from configuration")
        message += (
            "The following might help determine what the problem is:",
            f"`{error}`",
        )
        await ctx.respond("\n".join(message), ephemeral=True)

    async def cog_command_error(
        self, ctx: discord.ApplicationContext, error: Exception
    ) -> None:
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
