
import logging
from fnmatch import fnmatch
from config import appcmdname, appname, config, trace_on

LEVEL_TRACE = 5
LEVEL_TRACE_ALL = 3
logging.addLevelName(LEVEL_TRACE, "TRACE")
logging.addLevelName(LEVEL_TRACE_ALL, "TRACE_ALL")
logging.TRACE = LEVEL_TRACE  # type: ignore
logging.TRACE_ALL = LEVEL_TRACE_ALL  # type: ignore
logging.Logger.trace = lambda self, message, *args, **kwargs: self._log(  # type: ignore
    logging.TRACE,  # type: ignore
    message,
    args,
    **kwargs
)

def get_main_logger(sublogger_name: str = ''):
    return logging.getLogger()

def _trace_if(self: logging.Logger, condition: str, message: str, *args, **kwargs) -> None:
    if any(fnmatch(condition, p) for p in trace_on):
        self._log(logging.TRACE, message, args, **kwargs)  # type: ignore # we added it
        return

    self._log(logging.TRACE_ALL, message, args, **kwargs)  # type: ignore # we added it


logging.Logger.trace_if = _trace_if  # type: ignore


