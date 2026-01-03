from tortoise import Tortoise, fields
from tortoise.models import Model

from seeding_reward_bot.config import global_config

TORTOISE_MODELS = ["aerich.models", "seeding_reward_bot.db"]
TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": global_config["database"]["postgres"]["db_url"],
                "port": global_config["database"]["postgres"]["db_port"],
                "user": global_config["database"]["postgres"]["db_user"],
                "password": global_config["database"]["postgres"]["db_password"],
                "database": global_config["database"]["postgres"]["db_name"],
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

    def __str__(self):
        if self.player_name is not None:
            return self.player_name
        else:
            return self.player_id
