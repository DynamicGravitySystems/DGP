# coding: utf-8

import logging
import time
from pathlib import Path
from typing import Union, Callable

from PyQt5.QtCore import QThread, pyqtSignal

from dgp.core.oid import OID

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


class ProgressEvent:
    """Progress Event is used to define a request for the application to display
    a progress notification to the user, typically in the form of a QProgressBar

    ProgressEvents are emitted from the ProjectTreeModel model class, and should
    be captured by the application's MainWindow, which uses the ProgressEvent
    object to generate and display a QProgressDialog, or QProgressBar somewhere
    within the application.

    """
    def __init__(self, uid: OID, label: str = None, start: int = 0,
                 stop: int = 100, value: int = 0, modal: bool = True,
                 receiver: object = None):
        self.uid = uid
        self.label = label
        self.start = start
        self.stop = stop
        self._value = value
        self.modal = modal
        self.receiver = receiver

    @property
    def completed(self):
        return self._value >= self.stop

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, value: int) -> None:
        self._value = value


class ThreadedFunction(QThread):
    result = pyqtSignal(object)

    def __init__(self, functor, *args, parent):
        super().__init__(parent)
        self._functor = functor
        self._args = args

    def run(self):
        try:
            res = self._functor(*self._args)
            self.result.emit(res)
        except Exception as e:
            print(e)


def get_project_file(path: Path) -> Union[Path, None]:
    """
    Attempt to retrieve a project file (*.d2p) from the given dir path,
    otherwise signal failure by returning False.

    Parameters
    ----------
    path : Path
        Directory path to search for DGP project files

    Returns
    -------
    Path : absolute path to DGP JSON file if found, else None

    """
    # TODO: Read JSON and check for presence of a magic attribute that marks a project file
    for child in sorted(path.glob('*.json')):
        return child.resolve()
