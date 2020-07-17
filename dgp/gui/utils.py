# -*- coding: utf-8 -*-
import json
import logging
from pathlib import Path
from typing import Callable

from PyQt5.QtCore import QThread, pyqtSignal, pyqtBoundSignal

from dgp.core.models.project import GravityProject, AirborneProject
from dgp.core.oid import OID

__all__ = ['LOG_FORMAT', 'LOG_COLOR_MAP', 'LOG_LEVEL_MAP', 'ConsoleHandler',
           'ProgressEvent', 'ThreadedFunction', 'clear_signal',
           'load_project_from_path']

LOG_FORMAT = logging.Formatter(fmt="%(asctime)s:%(levelname)s - %(module)s:"
                                   "%(funcName)s :: %(message)s",
                               datefmt="%H:%M:%S")
LOG_COLOR_MAP = {'debug': 'blue', 'info': 'yellow', 'warning': 'brown',
                 'error': 'red', 'critical': 'orange'}
LOG_LEVEL_MAP = {'debug': logging.DEBUG, 'info': logging.INFO,
                 'warning': logging.WARNING, 'error': logging.ERROR,
                 'critical': logging.CRITICAL}
_loaders = {GravityProject.__name__: GravityProject,
            AirborneProject.__name__: AirborneProject}

_log = logging.getLogger(__name__)


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
            _log.exception(f"Exception executing {self._functor!r}")


def load_project_from_path(path: Path) -> GravityProject:
    """Search a directory path for a valid DGP json file, then load the project
    using the appropriate class loader.

    Any discovered .json files are loaded and parsed using a naive JSON loader,
    the top level object is then inspected for an `_type` attribute, which
    determines the project loader to use.

    The project's path attribute is updated to the path where it was loaded from
    upon successful decoding. This is to ensure any relative paths encoded in
    the project do not break if the project's directory has been moved/renamed.

    Parameters
    ----------
    path: :class:`pathlib.Path`
        Directory path which contains a valid DGP project .json file.
        If the path specified is not a directory, the parent is automatically
        used

    Raises
    ------
    :exc:`FileNotFoundError`
        If supplied `path` does not exist, or
        If no valid project JSON file could be loaded from the path


    ToDo: Use QLockFile to try and lock the project json file for exclusive use

    """
    if not path.exists():
        raise FileNotFoundError(f'Non-existent path supplied {path!s}')
    if not path.is_dir():
        path = path.parent

    for child in path.glob('*.json'):
        with child.open('r') as fd:
            raw_str = fd.read()
            raw_json: dict = json.loads(raw_str)

        loader = _loaders.get(raw_json.get('_type', None), None)
        if loader is not None:
            project = loader.from_json(raw_str)
            project.path = path
            return project
    raise FileNotFoundError(f'No valid DGP JSON file could be loaded from {path!s}')


def clear_signal(signal: pyqtBoundSignal):
    """Utility method to clear all connections from a bound signal"""
    while True:
        try:
            signal.disconnect()
        except TypeError:
            break
