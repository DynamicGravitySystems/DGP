# coding: utf-8

import pathlib

from pandas import DataFrame
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, pyqtBoundSignal

from dgp.lib.types import DataPacket
from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.trajectory_ingestor import import_trajectory


class LoadFile(QThread):
    progress = pyqtSignal(int)  # type: pyqtBoundSignal
    loaded = pyqtSignal()  # type: pyqtBoundSignal
    data = pyqtSignal(DataPacket)  # type: pyqtBoundSignal

    def __init__(self, path: pathlib.Path, datatype: str, flight_id: str, parent=None, **kwargs):
        super().__init__(parent)
        self._path = path
        self._dtype = datatype
        self._flight = flight_id
        self._functor = {'gravity': read_at1a, 'gps': import_trajectory}.get(datatype, None)

    def run(self):
        if self._dtype == 'gps':
            fields = ['mdy', 'hms', 'lat', 'long', 'ell_ht', 'ortho_ht', 'num_sats', 'pdop']
            df = self._functor(self._path, columns=fields, skiprows=1, timeformat='hms')
        else:
            df = self._functor(self._path)
        data = DataPacket(df, self._path, self._flight, self._dtype)
        self.data.emit(data)
        self.loaded.emit()
