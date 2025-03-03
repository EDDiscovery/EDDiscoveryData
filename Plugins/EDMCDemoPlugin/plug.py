import copy
import importlib
import logging
import operator
import sys
import pathlib
from config import config
from typing import Any, Mapping, MutableMapping

from EDMCLogging import get_main_logger

logger = get_main_logger()


PLUGINS = []

class Plugin:
     def __init__(self, name: str, loadfile : pathlib.Path): 
        self.name: str = name  # Display name.
        self.folder: str | None = name  # basename of plugin folder. None for internal plugins.
        self.module = None  # None for disabled plugins.
        
        if loadfile:
            filename = 'plugin_'
            filename += name.encode(encoding='ascii', errors='replace').decode('utf-8').replace('.', '_')
            spec = importlib.util.spec_from_file_location(filename, loadfile)
            # Replaces older load_module() code. Includes a safety check that the module name is set.
            if spec is not None and spec.loader is not None:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module.__name__] = module
                spec.loader.exec_module(module)
                if getattr(module, 'plugin_start3', None):
                    newname = module.plugin_start3(pathlib.Path(loadfile).resolve().parent)
                    self.name = str(newname) if newname else self.name
                    self.module = module
     
     def _get_func(self, funcname: str):
            """
            Get a function from a plugin.

            :param funcname:
            :returns: The function, or None if it isn't implemented.
            """
            return getattr(self.module, funcname, None)

 
def _load_found_plugins():
    found = []
    # Load any plugins that are also packages first, but note it's *still*
    # 100% relying on there being a `load.py`, as only that will be loaded.
    # The intent here is to e.g. have EDMC-Overlay load before any plugins
    # that depend on it.

    plugin_files = sorted(config.plugin_dir_path.iterdir(), key=lambda p: (
        not (p / '__init__.py').is_file(), p.name.lower()))

    for plugin_file in plugin_files:
        name = plugin_file.name
        if not (config.plugin_dir_path / name).is_dir() or name.startswith(('.', '_')):
            pass
        else:
            try:
                # Add plugin's folder to load path in case plugin has internal package dependencies
                sys.path.append(str(config.plugin_dir_path / name))

                # Create a logger for this 'found' plugin.  Must be before the load.py is loaded.
                found.append(Plugin(name, config.plugin_dir_path / name / 'load.py'))
            except Exception:
                print("OOOps")
                pass
    return found

def load_plugins():
     found = _load_found_plugins()
     PLUGINS.extend(sorted(found, key=lambda p: operator.attrgetter('name')(p).lower()))

def provides(fn_name: str) -> list[str]:
    """
    Find plugins that provide a function.

    :param fn_name:
    :returns: list of names of plugins that provide this function
    .. versionadded:: 3.0.2
    """
    return [p.name for p in PLUGINS if p._get_func(fn_name)]


def invoke(
    plugin_name: str, fallback: str | None, fn_name: str, *args: Any
) -> str | None:
    """
    Invoke a function on a named plugin.

    :param plugin_name: preferred plugin on which to invoke the function
    :param fallback: fallback plugin on which to invoke the function, or None
    :param fn_name:
    :param *args: arguments passed to the function
    :returns: return value from the function, or None if the function was not found
    .. versionadded:: 3.0.2
    """
    for plugin in PLUGINS:
        if plugin.name == plugin_name:
            plugin_func = plugin._get_func(fn_name)
            if plugin_func is not None:
                return plugin_func(*args)

    for plugin in PLUGINS:
        if plugin.name == fallback:
            plugin_func = plugin._get_func(fn_name)
            assert plugin_func, plugin.name  # fallback plugin should provide the function
            return plugin_func(*args)

    return None

def notify_stop() -> str | None:
    """
    Notify each plugin that the program is closing.

    If your plugin uses threads then stop and join() them before returning.
    .. versionadded:: 2.3.7
    """
    error = None
    for plugin in PLUGINS:
        plugin_stop = plugin._get_func('plugin_stop')
        if plugin_stop:
            try:
                logger.info(f'Asking plugin "{plugin.name}" to stop...')
                newerror = plugin_stop()
                error = error or newerror
            except Exception:
                logger.exception(f'Plugin "{plugin.name}" failed')

    logger.info('Done')

    return error


def _notify_prefs_plugins(fn_name: str, cmdr: str | None, is_beta: bool) -> None:
    for plugin in PLUGINS:
        prefs_callback = plugin._get_func(fn_name)
        if prefs_callback:
            try:
                prefs_callback(cmdr, is_beta)
            except Exception:
                logger.exception(f'Plugin "{plugin.name}" failed')


def notify_prefs_cmdr_changed(cmdr: str | None, is_beta: bool) -> None:
    """
    Notify plugins that the Cmdr was changed while the settings dialog is open.

    Relevant if you want to have different settings for different user accounts.
    :param cmdr: current Cmdr name (or None).
    :param is_beta: whether the player is in a Beta universe.
    """
    _notify_prefs_plugins("prefs_cmdr_changed", cmdr, is_beta)


def notify_prefs_changed(cmdr: str | None, is_beta: bool) -> None:
    """
    Notify plugins that the settings dialog has been closed.

    The prefs frame and any widgets you created in your `get_prefs()` callback
    will be destroyed on return from this function, so take a copy of any
    values that you want to save.
    :param cmdr: current Cmdr name (or None).
    :param is_beta: whether the player is in a Beta universe.
    """
    _notify_prefs_plugins("prefs_changed", cmdr, is_beta)


def notify_journal_entry(
    cmdr: str, is_beta: bool, system: str | None, station: str | None,
    entry: MutableMapping[str, Any],
    state: Mapping[str, Any]
) -> str | None:
    """
    Send a journal entry to each plugin.

    :param cmdr: The Cmdr name, or None if not yet known
    :param system: The current system, or None if not yet known
    :param station: The current station, or None if not docked or not yet known
    :param entry: The journal entry as a dictionary
    :param state: A dictionary containing info about the Cmdr, current ship and cargo
    :param is_beta: whether the player is in a Beta universe.
    :returns: Error message from the first plugin that returns one (if any)
    """
    if entry['event'] in 'Location':
        logger.trace_if('journal.locations', 'Notifying plugins of "Location" event')

    error = None
    for plugin in PLUGINS:
        journal_entry = plugin._get_func('journal_entry')
        if journal_entry:
            try:
                # Pass a copy of the journal entry in case the callee modifies it
                newerror = journal_entry(cmdr, is_beta, system, station, dict(entry), dict(state))
                error = error or newerror
            except Exception:
                logger.exception(f'Plugin "{plugin.name}" failed')
    return error


def notify_journal_entry_cqc(
    cmdr: str, is_beta: bool,
    entry: MutableMapping[str, Any],
    state: Mapping[str, Any]
) -> str | None:
    """
    Send an in-CQC journal entry to each plugin.

    :param cmdr: The Cmdr name, or None if not yet known
    :param entry: The journal entry as a dictionary
    :param state: A dictionary containing info about the Cmdr, current ship and cargo
    :param is_beta: whether the player is in a Beta universe.
    :returns: Error message from the first plugin that returns one (if any)
    """
    error = None
    for plugin in PLUGINS:
        cqc_callback = plugin._get_func('journal_entry_cqc')
        if cqc_callback is not None and callable(cqc_callback):
            try:
                # Pass a copy of the journal entry in case the callee modifies it
                newerror = cqc_callback(cmdr, is_beta, copy.deepcopy(entry), copy.deepcopy(state))
                error = error or newerror

            except Exception:
                logger.exception(f'Plugin "{plugin.name}" failed while handling CQC mode journal entry')

    return error


def notify_dashboard_entry(cmdr: str, is_beta: bool, entry: MutableMapping[str, Any],) -> str | None:
    """
    Send a status entry to each plugin.

    :param cmdr: The piloting Cmdr name
    :param is_beta: whether the player is in a Beta universe.
    :param entry: The status entry as a dictionary
    :returns: Error message from the first plugin that returns one (if any)
    """
    error = None
    for plugin in PLUGINS:
        status = plugin._get_func('dashboard_entry')
        if status:
            try:
                # Pass a copy of the status entry in case the callee modifies it
                newerror = status(cmdr, is_beta, dict(entry))
                error = error or newerror
            except Exception:
                logger.exception(f'Plugin "{plugin.name}" failed')
    return error


