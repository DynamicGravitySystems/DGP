# -*- coding: utf-8 -*-
import logging
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from dgp.core import DataType
from dgp.core.hdf5_manager import HDF5Manager
from dgp.core.oid import OID
from dgp.core.types.enumerations import Icon
from dgp.core.controllers.controller_interfaces import IDataSetController, IBaseController
from dgp.core.controllers.controller_helpers import show_in_explorer
from dgp.core.models.datafile import DataFile


class DataFileController(IBaseController):
    def __init__(self, datafile: DataFile, dataset=None):
        super().__init__()
        self._datafile = datafile
        self._dataset: IDataSetController = dataset
        self.log = logging.getLogger(__name__)

        self.set_datafile(datafile)

        self._bindings = [
            ('addAction', ('Properties', self._properties_dlg)),
            ('addAction', (Icon.OPEN_FOLDER.icon(), 'Show in Explorer',
                           self._launch_explorer))
        ]

    @property
    def uid(self) -> OID:
        try:
            return self._datafile.uid
        except AttributeError:
            return None

    @property
    def dataset(self) -> IDataSetController:
        return self._dataset

    @property
    def menu(self):  # pragma: no cover
        return self._bindings

    @property
    def group(self):
        return self._datafile.group

    @property
    def datamodel(self) -> object:
        return self._datafile

    def set_datafile(self, datafile: DataFile):
        self._datafile = datafile
        if datafile is None:
            self.setText("No Data")
            self.setToolTip("No Data")
            self.setData(None, Qt.UserRole)
        else:
            self.setText(datafile.label)
            self.setToolTip("Source path: {!s}".format(datafile.source_path))
            self.setData(datafile, role=Qt.UserRole)
            if self._datafile.group is DataType.GRAVITY:
                self.setIcon(Icon.GRAVITY.icon())
            elif self._datafile.group is DataType.TRAJECTORY:
                self.setIcon(Icon.TRAJECTORY.icon())

    def _properties_dlg(self):
        if self._datafile is None:
            return
        # TODO: Launch dialog to show datafile properties (name, path, data etc)
        data = HDF5Manager.load_data(self._datafile, self.dataset.hdfpath)
        self.log.info(f'\n{data.describe()}')

    def _launch_explorer(self):
        if self._datafile is not None:
            show_in_explorer(self._datafile.source_path.parent)
