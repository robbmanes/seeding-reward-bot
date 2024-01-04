from glowbot.config import global_config
import logging
from tortoise import Tortoise, fields
from tortoise.models import Model

class GlowDatabase(Tortoise):
    """
    Extension of the base Tortoise database for Glowbot.
    Only supports postgresql, and self-generates configuration and initialization.
    """

    models = ['aerich.models', 'glowbot.db']

    def __init__(self, event_loop):
        super().__init__()

        self.logger = logging.getLogger(__package__)
        self.db_config = self.generate_db_config()

        self.logger.info("Loading ORM for models: %s" % (self.models))
        event_loop.run_until_complete(Tortoise.init(config=self.db_config))
        event_loop.run_until_complete(Tortoise.generate_schemas())

    def generate_db_config(self):
        db_config = {
            'connections': {
                'default': {
                    'engine': "tortoise.backends.asyncpg",
                    'credentials': {
                        'host': global_config['database']['postgres']['db_url'],
                        'port': global_config['database']['postgres']['db_port'],
                        'user': global_config['database']['postgres']['db_user'],
                        'password': global_config['database']['postgres']['db_password'],
                        'database': global_config['database']['postgres']['db_name'],
                    },
                },
            },
            'apps': {
                'glowbot': {
                    'models': self.models,
                    'default_connection': 'default',
                },
            },
        }

        return db_config

async def get_player_by_discord_id(id):
    """
    Performs a lookup for a user based on their steam_64_id <=> discord_id.
    If no result, None is returned indicating the user has no entry or hasn't registered.
    """
    query_set = await HLL_Player.filter(discord_id__contains=id)
    if len(query_set) == 0:
        return None
    elif len(query_set) != 1:
        self.logger.fatal("Multiple discord_id's found for %s!" % (id))
        raise
    else:
        return query_set[0]
async def get_player_by_steam_id(id):
    """
    Performs a lookup for a user based on their steam_64_id <=> discord_id.
    If no result, None is returned indicating the user has no entry or hasn't registered.
    """
    query_set = await HLL_Player.filter(steam_id_64__contains=id)
    if len(query_set) == 0:
        return None
    elif len(query_set) != 1:
        self.logger.fatal("Multiple entries found for %s!" % (id))
        raise
    else:
        return query_set[0]

class HLL_Player(Model):
    """
    Model representing a player <=> discord relationship.
    """
    steam_id_64 = fields.BigIntField(description='Steam64Id for the player')
    player_name = fields.TextField(description='Player\'s stored name', null=True)
    discord_id = fields.TextField(description='Discord ID for player', null=True)
    seeding_time_balance = fields.TimeDeltaField(description='Amount of unspent seeding hours')
    total_seeding_time = fields.TimeDeltaField(description='Total amount of time player has spent seeding')
    last_seed_check = fields.DatetimeField(description='Last time the seeder was seen during a seed check')

    def __str__(self):
        if self.player_name is not None:
            return self.player_name
        else:
            return self.steam_id_64