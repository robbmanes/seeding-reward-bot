import logging

import tomli


class Configuration(object):

    def __init__(self, config_file='config.toml'):
        self.logger = logging.getLogger(__package__)
        self.config_file = config_file
        self.settings = self.parse_config(self.config_file)

    def parse_config(self, config_file):
        try:
            with open(config_file, "rb") as f:
                config = tomli.load(f)
            return config
        except Exception as e:
            self.logger.fatal(
                f"Failed to parse configuration file {config_file}: {e!s}"
            )


global_config_object = Configuration()
global_config = global_config_object.settings
