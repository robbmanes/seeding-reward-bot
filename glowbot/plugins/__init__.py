import glob
import importlib
import logging
import os


loaded_plugins = []

try:
    plugin_paths = []
    plugin_paths_raw = glob.glob(os.path.join(os.path.dirname(__file__), '*.py'))
    for f in plugin_paths_raw:
        if os.path.isfile(f) and not f.endswith('__init__.py'):
            plugin_paths.append(f)

    __all__ = [os.path.basename(f)[:-3] for f in plugin_paths]
    for plugin in __all__:
        loaded_plugins.append(importlib.import_module('glowbot.plugins.' + plugin, package=None))
    
except Exception as e:
    logging.fatal("Failed loading subplugins: %s" % (e))