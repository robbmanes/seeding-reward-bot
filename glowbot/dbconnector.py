import asyncio
from databases import Database
import logging


class DBConnection(object):

    def __init__(self, db_config):
        self.logger = logging.getLogger("Database")
        self.config = db_config
        try:
            self.database = Database('postgresql+asyncpg://%s:%s@%s' % (
                self.config['database_user'],
                self.config['database_password'],
                self.config['database_url'],
                )
            )
            asyncio.run(self.database.connect())
        except Exception as e:
            self.logger.fatal("Failed to connect to database: %s" % (e))