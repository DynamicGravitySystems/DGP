# -*- coding: utf-8 -*-
import inspect
import logging
from pathlib import Path
from typing import Callable

from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from pandas import DataFrame


class FileLoader(QThread):
    completed = pyqtSignal(DataFrame, Path)
    error = pyqtSignal(Exception)

    def __init__(self, path: Path, method: Callable, parent, **kwargs):
        super().__init__(parent=parent)
        self.log = logging.getLogger(__name__)
        self._path = Path(path)
        self._method = method
        self._kwargs = kwargs

    def run(self):
        try:
            sig = inspect.signature(self._method)
            kwargs = {k: v for k, v in self._kwargs.items() if k in sig.parameters}
            result = self._method(str(self._path), **kwargs)
        except Exception as e:
            self.log.exception("Error loading datafile: %s" % str(self._path))
            self.error.emit(e)
        else:
            self.completed.emit(result, self._path)


