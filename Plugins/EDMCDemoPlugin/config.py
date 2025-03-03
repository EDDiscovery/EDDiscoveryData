# EDD bastard version of config system from EDMC implementing the same interfaces

import pathlib
import sys
import semantic_version

appname = 'EDMarketConnector'
applongname = 'E:D Market Connector'
appcmdname = 'EDMC'
copyright = '2015-2019 Jonathan Harris, 2020-2024 EDCD'
trace_on: list[str] = []

def appversion() -> semantic_version.Version:
    return semantic_version.Version("5.12.1")

class EDDConfigSystem:
    EDDConfig = dict()    
    
    respath_path: pathlib.Path
    plugin_dir_path : pathlib.Path
    
    def __init__(self) -> None:
        self.respath_path = pathlib.Path(".")
        self.plugin_dir_path = pathlib.Path("plugins")
        #print("Constructor of Config")
        pass
        
    def SetEDDConfig(self,eddconfig) -> None:   # make EDDConfig be the EDDIF object
        self.EDDConfig = eddconfig
        #print("Set Config")

    def shutting_down(self) -> bool:        # always false
        return False

    def get_str(self, key: str, *, default: str | None = None) -> str:
        """
        Return the string referred to by the given key if it exists, or the default.

        Implements :meth:`AbstractConfig.get_str`.
        """

        if key in self.EDDConfig:
            res = self.EDDConfig[key]
        else:
            return default    
       
        if not isinstance(res, str):
            raise ValueError(f'Data from registry is not a string: {type(res)=} {res=}')

        return res

    def get_list(self, key: str, *, default: list | None = None) -> list:
        """
        Return the list referred to by the given key if it exists, or the default.

        Implements :meth:`AbstractConfig.get_list`.
        """
        if key in self.EDDConfig:
            res = self.EDDConfig[key]
        else:
            return default    

        if not isinstance(res, list):
            raise ValueError(f'Data from registry is not a list: {type(res)=} {res}')

        return res

    def getint(self, key: str, *, default: int = 0) -> int:
        return self.get_int(key, default=default)

    def get_int(self, key: str, *, default: int = 0) -> int:
        """
        Return the int referred to by key if it exists in the config.

        Implements :meth:`AbstractConfig.get_int`.
        """
        
        if key in self.EDDConfig:
            res = self.EDDConfig[key]
        else:
            return default    

        if not isinstance(res, int):
            raise ValueError(f'Data from registry is not an int: {type(res)=} {res}')

        return res

    def get_bool(self, key: str, *, default: bool | None = None) -> bool:
        """
        Return the bool referred to by the given key if it exists, or the default.

        Implements :meth:`AbstractConfig.get_bool`.
        """
        res = self.get_int(key, default=default)  # type: ignore
        if res is None:
            return default  # Yes it could be None, but we're _assuming_ that people gave us a default

        return bool(res)

    def set(self, key: str, val: int | str | list[str] | bool) -> None:
        """
        Set the given key's data to the given value.

        Implements :meth:`AbstractConfig.set`.
        """
        
        self.EDDConfig[key] = val

    def delete(self, key: str, *, suppress=False) -> None:
        """
        Delete the given key from the config.

        'key' is relative to the base Registry path we use.

        Implements :meth:`AbstractConfig.delete`.
        """
        
        self.EDDConfig.pop(key,None)

    def save(self) -> None:
        """
        Save the configuration.

        Not required
        """
        pass

    def close(self):
        """
        Close this config and release any associated resources.

        Implements :meth:`AbstractConfig.close`.
        """
        pass

def get_config(*args, **kwargs):
    """
    Get the appropriate config class for the current platform.

    :param args: Args to be passed through to implementation.
    :param kwargs: Args to be passed through to implementation.
    :return: Instance of the implementation.
    """
    if sys.platform == "win32":  # pragma: sys-platform-win32
        return EDDConfigSystem(*args, **kwargs)

    raise ValueError(f'Unknown platform: {sys.platform=}')

config = get_config()


