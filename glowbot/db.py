from glowbot.config import global_config
import logging
from tortoise import Tortoise

class GlowDatabase(Tortoise):
    """
    Extension of the base Tortoise database for Glowbot.
    Only supports postgresql, and self-generates configuration and initialization.
    """

    models = ['aerich.models', 'glowbot.hell_let_loose']

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