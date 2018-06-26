# coding: utf-8

import pathlib
import logging
import inspect

from PyQt5.QtCore import pyqtSignal, QThread, pyqtBoundSignal
from pandas import DataFrame

import dgp.lib.gravity_ingestor as gi
import dgp.lib.trajectory_ingestor as ti
from core.types.enumerations import DataTypes, GravityTypes

_log = logging.getLogger(__name__)


def _not_implemented(*args, **kwargs):
    """Temporary method, raises NotImplementedError for ingestor methods that
    have not yet been defined."""
    raise NotImplementedError()


# TODO: Work needs to be done on ZLS as the data format is completely different
# ZLS data is stored in a directory with the filenames delimiting hours
GRAVITY_INGESTORS = {
    GravityTypes.AT1A: gi.read_at1a,
    GravityTypes.AT1M: _not_implemented,
    GravityTypes.TAGS: _not_implemented,
    GravityTypes.ZLS: _not_implemented
}


# TODO: I think this class should handle Loading only, and emit a DataFrame
# We're doing too many things here by having the loader thread also write the
#  reuslt out. Use another method to generated the DataSource
class LoaderThread(QThread):
    result = pyqtSignal(DataFrame)  # type: pyqtBoundSignal
    error = pyqtSignal(tuple)  # type: pyqtBoundSignal

    def __init__(self, method, path, dtype=None, parent=None, **kwargs):
        super().__init__(parent=parent)
        self.log = logging.getLogger(__name__)
        self._method = method
        self._dtype = dtype
        self._kwargs = kwargs
        self.path = pathlib.Path(path)

    def run(self):
        """Called on thread.start()
        Exceptions must be caught within run, as they fall outside the
        context of the start() method, and thus cannot be handled properly
        outside of the thread execution context."""
        try:
            df = self._method(self.path, **self._kwargs)
        except Exception as e:
            # self.error.emit((True, e))
            _log.exception("Error loading datafile: {} of type: {}".format(
                self.path, self._dtype.name))
            self.error.emit((True, e))
        else:
            self.result.emit(df)
            self.error.emit((False, None))

    @classmethod
    def from_gravity(cls, parent, path, subtype=GravityTypes.AT1A, **kwargs):
        """
        Convenience method to generate a gravity LoaderThread with appropriate
        method based on gravity subtype.

        Parameters
        ----------
        parent
        path : pathlib.Path
        subtype
        kwargs

        Returns
        -------

        """
        # Inspect the subtype method and cull invalid parameters
        method = GRAVITY_INGESTORS[subtype]
        sig = inspect.signature(method)
        kwds = {k: v for k, v in kwargs.items() if k in sig.parameters}

        if subtype == GravityTypes.ZLS:
            # ZLS will inspect entire directory and parse file names
            path = path.parent

        return cls(method=method, path=path, parent=parent,
                   dtype=DataTypes.GRAVITY, **kwds)

    @classmethod
    def from_gps(cls, parent, path, subtype, **kwargs):
        """

        Parameters
        ----------
        parent
        path
        subtype
        kwargs

        Returns
        -------

        """
        return cls(method=ti.import_trajectory, path=path, parent=parent,
                   timeformat=subtype.name.lower(), dtype=DataTypes.TRAJECTORY,
                   **kwargs)


def get_loader(parent, path, dtype, subtype, on_complete, on_error, **kwargs):
    if dtype == DataTypes.GRAVITY:
        ld = LoaderThread.from_gravity(parent, path, subtype, **kwargs)
    else:
        ld = LoaderThread.from_gps(parent, path, subtype, **kwargs)

    if on_complete is not None and callable(on_complete):
        ld.result.connect(on_complete)
    if on_error is not None and callable(on_error):
        ld.error.connect(on_error)
    return ld
