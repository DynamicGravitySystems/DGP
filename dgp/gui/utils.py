# coding: utf-8

import logging
from pathlib import Path
from typing import Union, Callable

LOG_FORMAT = logging.Formatter(fmt="%(asctime)s:%(levelname)s - %(module)s:"
                                   "%(funcName)s :: %(message)s",
                               datefmt="%H:%M:%S")
LOG_COLOR_MAP = {'debug': 'blue', 'info': 'yellow', 'warning': 'brown',
                 'error': 'red', 'critical': 'orange'}
LOG_LEVEL_MAP = {'debug': logging.DEBUG, 'info': logging.INFO,
                 'warning': logging.WARNING, 'error': logging.ERROR,
                 'critical': logging.CRITICAL}


class ConsoleHandler(logging.Handler):
    """
    Custom Logging Handler allowing the specification of a custom destination
    e.g. a QTextEdit area.
    """
    def __init__(self, destination: Callable[[str, str], None]):
        """
        Initialize the Handler with a destination function to send logs to.
        Destination should take 2 parameters, however emit will fallback to
        passing a single parameter on exception.
        :param destination: callable function accepting 2 parameters:
        (log entry, log level name)
        """
        super().__init__()
        self._dest = destination

    def emit(self, record: logging.LogRecord):
        """Emit the log record, first running it through any specified
        formatter."""
        entry = self.format(record)
        try:
            self._dest(entry, record.levelname.lower())
        except TypeError:
            self._dest(entry)


def get_project_file(path: Path) -> Union[Path, None]:
    """
    Attempt to retrieve a project file (*.d2p) from the given dir path,
    otherwise signal failure by returning False.
    :param path: str or pathlib.Path : Directory path to project
    :return: pathlib.Path : absolute path to *.d2p file if found, else False
    """
    for child in sorted(path.glob('*.d2p')):
        return child.resolve()
    return None
