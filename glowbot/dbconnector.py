import asyncio
from databases import Database
import logging


class DBConnection(object):

    def __init__(self, db_config):
        self.logger = logging.getLogger("Database")
        self.config = db_config
        try:
            self.database = Database('mysql+aimoysql://%s' % (self.config['database_url']))
            asyncio.run(database.connect())
        except Exception as e:
            self.logger.fatal("Failed to connect to database: %s" % (e))