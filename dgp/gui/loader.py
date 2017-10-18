# coding: utf-8

import pathlib
from typing import List

from pandas import DataFrame
from PyQt5.QtCore import pyqtSignal, QThread, pyqtBoundSignal

from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.trajectory_ingestor import import_trajectory


class LoadFile(QThread):
    """Defines a QThread object whose job is to load (potentially large) datafiles in a Thread."""
    progress = pyqtSignal(int)  # type: pyqtBoundSignal
    loaded = pyqtSignal()  # type: pyqtBoundSignal
    # data = pyqtSignal(DataPacket)  # type: pyqtBoundSignal
    data = pyqtSignal(DataFrame, pathlib.Path, str)

    def __init__(self, path: pathlib.Path, datatype: str, flight_id: str, fields: List=None, parent=None, **kwargs):
        super().__init__(parent)
        # TODO: Add type checking to path, ensure it is a pathlib.Path (not str) as the pyqtSignal expects a Path
        self._path = path
        self._dtype = datatype
        self._flight = flight_id
        self._functor = {'gravity': read_at1a, 'gps': import_trajectory}.get(datatype, None)
        self._fields = fields

    def run(self):
        if self._dtype == 'gps':
            df = self._load_gps()
        else:
            df = self._load_gravity()
        self.progress.emit(1)
        # self.data.emit(data)
        self.data.emit(df, pathlib.Path(self._path), self._dtype)
        self.loaded.emit()

    def _load_gps(self):
        if self._fields is not None:
            fields = self._fields
        else:
            fields = ['mdy', 'hms', 'lat', 'long', 'ortho_ht', 'ell_ht', 'num_sats', 'pdop']
        return self._functor(self._path, columns=fields, skiprows=1, timeformat='hms')

    def _load_gravity(self):
        if self._fields is None:
            return self._functor(self._path)
        else:
            return self._functor(self._path, fields=self._fields)
