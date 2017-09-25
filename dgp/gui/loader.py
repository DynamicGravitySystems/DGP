# coding: utf-8

import pathlib

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

    def __init__(self, path: pathlib.Path, datatype: str, flight_id: str, parent=None, **kwargs):
        super().__init__(parent)
        self._path = path
        self._dtype = datatype
        self._flight = flight_id
        self._functor = {'gravity': read_at1a, 'gps': import_trajectory}.get(datatype, None)

    def run(self):
        if self._dtype == 'gps':
            fields = ['mdy', 'hms', 'lat', 'long', 'ortho_ht', 'ell_ht', 'num_sats', 'pdop']
            df = self._functor(self._path, columns=fields, skiprows=1, timeformat='hms')
        else:
            df = self._functor(self._path)
        # data = DataPacket(df, self._path, self._dtype)
        self.progress.emit(1)
        # self.data.emit(data)
        self.data.emit(df, self._path, self._dtype)
        self.loaded.emit()
