# coding: utf-8

import pathlib
from typing import List

from PyQt5.QtCore import pyqtSignal, QThread, pyqtBoundSignal

import dgp.lib.types as types
import dgp.lib.datamanager as dm
from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.trajectory_ingestor import import_trajectory


class LoadFile(QThread):
    """
    LoadFile is a threaded interface used to load and ingest a raw source
    data file, i.e. gravity or trajectory data.
    Upon import the data is exported to an HDF5 store for further use by the
    application.
    """
    progress = pyqtSignal(int)  # type: pyqtBoundSignal
    loaded = pyqtSignal()  # type: pyqtBoundSignal
    data = pyqtSignal(types.DataSource)  # type: pyqtBoundSignal

    def __init__(self, path: pathlib.Path, datatype: str, fields: List=None,
                 parent=None, **kwargs):
        super().__init__(parent)
        self._path = pathlib.Path(path)
        self._dtype = datatype
        self._functor = {'gravity': read_at1a,
                         'gps': import_trajectory}.get(datatype, None)
        self._fields = fields

    def run(self):
        if self._dtype == 'gps':
            df = self._load_gps()
        else:
            df = self._load_gravity()
        self.progress.emit(1)
        uid = dm.get_manager().save_data('hdf5', df)
        cols = [col for col in df.keys()]
        dsrc = types.DataSource(uid, self._path, cols, self._dtype)
        self.data.emit(dsrc)
        self.loaded.emit()

    def _load_gps(self):
        if self._fields is not None:
            fields = self._fields
        else:
            fields = ['mdy', 'hms', 'lat', 'long', 'ortho_ht', 'ell_ht',
                      'num_sats', 'pdop']
        return self._functor(self._path, columns=fields, skiprows=1,
                             timeformat='hms')

    def _load_gravity(self):
        if self._fields is None:
            return self._functor(self._path)
        else:
            return self._functor(self._path, fields=self._fields)
