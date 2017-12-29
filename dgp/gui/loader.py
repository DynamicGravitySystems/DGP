# coding: utf-8

import pathlib
import logging
from typing import List

from PyQt5.QtCore import pyqtSignal, QThread, pyqtBoundSignal

import dgp.lib.types as types
import dgp.lib.datamanager as dm
from dgp.lib.enums import DataTypes
from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.trajectory_ingestor import import_trajectory

_log = logging.getLogger(__name__)


class LoadFile(QThread):
    """
    LoadFile is a threaded interface used to load and ingest a raw source
    data file, i.e. gravity or trajectory data.
    Upon import the data is exported to an HDF5 store for further use by the
    application.
    """
    error = pyqtSignal(bool)
    data = pyqtSignal(types.DataSource)  # type: pyqtBoundSignal

    def __init__(self, path: pathlib.Path, dtype: DataTypes, fields: List=None,
                 parent=None, **kwargs):
        super().__init__(parent)
        self._path = pathlib.Path(path)
        self._dtype = dtype
        self._fields = fields
        self._skiprow = kwargs.get('skiprow', None)
        print("Loader has skiprow: ", self._skiprow)

    def run(self):
        """Executed on thread.start(), performs long running data load action"""
        if self._dtype == DataTypes.TRAJECTORY:
            try:
                df = self._load_gps()
            except (ValueError, Exception):
                _log.exception("Exception loading Trajectory data")
                self.error.emit(True)
                return
        elif self._dtype == DataTypes.GRAVITY:
            try:
                df = self._load_gravity()
            except (ValueError, Exception):
                _log.exception("Exception loading Gravity data")
                self.error.emit(True)
                return
        else:
            _log.warning("Invalid datatype set for LoadFile run()")
            self.error.emit(True)
            return
        # Export data to HDF5, get UID reference to pass along
        uid = dm.get_manager().save_data(dm.HDF5, df)
        cols = [col for col in df.keys()]
        dsrc = types.DataSource(uid, self._path.name, cols, self._dtype)
        self.data.emit(dsrc)
        self.error.emit(False)

    def _load_gps(self):
        if self._fields is not None:
            fields = self._fields
        else:
            fields = ['mdy', 'hms', 'latitude', 'longitude', 'ortho_ht',
                      'ell_ht', 'num_sats', 'pdop']
        return import_trajectory(self._path,
                                 columns=fields,
                                 skiprows=self._skiprow,
                                 timeformat='hms')

    def _load_gravity(self):
        """Load gravity data using AT1A format"""
        return read_at1a(self._path, fields=self._fields,
                         skiprows=self._skiprow)
