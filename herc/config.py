import pyhocon
import threading
import traceback
import sys
import importlib

_config = None
_configlock = threading.Lock()

class ConfigNotLoadedException(Exception):
    """You probably tried to access a config value without calling load_config() first."""
    pass

def load_config(configlocs):
    """Attempts to load Herc config file.
    configlocs: A list of file paths to look for config files in.
    The first one that loads correctly will be used."""
    global _config
    excs = []
    with _configlock:
        if _config is None:
            for conf in configlocs:
                try:
                    _config = pyhocon.ConfigFactory.parse_file(conf)
                    break
                except BaseException as be:
                    excs.append(be)

        if _config is None:
            #still? must have failed
            print("Fatal error - failed to load Herc config file!")
            print("Locations checked:", configlocs)
            for exc in excs:
                print("Errors, in order:")
                traceback.print_tb(exc)
            sys.exit(1)

def get(*args, **kwargs):
    """Gets a value from the config file."""
    if _config is None:
        raise ConfigNotLoadedException("No config loaded. Did you forget to call config.load_config()?")
    return _config.get(*args, **kwargs)

def importclass(classpath):
    """Turns a string representing a Python class into the actual class object.
    May return ImportError or AttributeError if you do something that's not legit."""
    path = classpath.rsplit( ".", 1 )

    # load the module, will raise ImportError if module cannot be loaded
    m = importlib.import_module(path[0])

    # get the class, will raise AttributeError if class cannot be found
    return getattr(m, path[1])

def getclass(*args, **kwargs):
    """Gets a value from the config file and attempts to import it as a Python class.
    May return ImportError or AttributeError if you do something that's not legit."""
    return importclass( get(*args, **kwargs) )
