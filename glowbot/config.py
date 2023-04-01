import tomli
import logging


class Configuration(object):

    def __init__(self, config_file='config.toml'):
        self.config_file = config_file
        self.settings = self.parse_config(self.config_file)
        self.logger = logging.getLogger(__package__)
        
    def parse_config(self, config_file):
        try:
            with open(config_file, "rb") as f:
                config = tomli.load(f)
            return config
        except Exception as e:
            self.logger.fatal("Failed to parse configuration file %s: %s" % (config_file, e))