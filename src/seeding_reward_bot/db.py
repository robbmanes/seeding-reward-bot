from tortoise import Tortoise, fields
from tortoise.indexes import PartialIndex
from tortoise.models import Model

from seeding_reward_bot.config import global_config

TORTOISE_MODELS = ["aerich.models", "seeding_reward_bot.db"]
TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": global_config.db_host,
                "port": global_config.db_port,
                "user": global_config.db_user,
                "password": global_config.db_password,
                "database": global_config.db_name,
            },
        },
    },
    "apps": {
        "seedbot": {
            "models": TORTOISE_MODELS,
            "default_connection": "default",
        },
    },
}


async def init():
    await Tortoise.init(config=TORTOISE_ORM)


async def close():
    await Tortoise.close_connections()


class HLL_Player(Model):
    """
    Model representing a player <=> discord relationship.
    """

    class Meta:
        indexes = [
            PartialIndex(fields=["hidden"], condition={"hidden": True}),
        ]

    player_id = fields.TextField(description="Player ID for the player")  # UNIQUE in DB
    player_name = fields.TextField(description="Player's stored name", null=True)
    discord_id = fields.BigIntField(
        description="Discord ID for player", null=True, unique=True
    )
    seeding_time_balance = fields.TimeDeltaField(
        description="Amount of unspent seeding hours"
    )
    total_seeding_time = fields.TimeDeltaField(
        description="Total amount of time player has spent seeding"
    )
    last_seed_check = fields.DatetimeField(
        description="Last time the seeder was seen during a seed check"
    )
    hidden = fields.BooleanField(
        description="Player is hidden from stats", default=False
    )

    def __str__(self):
        if self.player_name is not None:
            return self.player_name
        else:
            return self.player_id


class Seeding_Session(Model):
    """
    Model representing a one to many relation of a player's seeding sessions.
    """

    class Meta:
        unique_together = ("hll_player", "server", "start_time")

    hll_player = fields.ForeignKeyField("seedbot.HLL_Player", db_index=True)
    server = fields.IntField(description="Server session took place on")
    start_time = fields.DatetimeField(description="Start time of seeding session")
    end_time = fields.DatetimeField(
        description="End time of seeding session", db_index=True
    )
