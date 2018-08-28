# -*- coding: utf-8 -*-
import logging
from typing import cast, Generator

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from dgp.core import DataType
from dgp.core.hdf5_manager import HDF5Manager
from dgp.core.oid import OID
from dgp.core.types.enumerations import Icon
from dgp.core.controllers.controller_interfaces import IDataSetController, AbstractController
from dgp.core.controllers.controller_helpers import show_in_explorer
from dgp.core.models.datafile import DataFile


class DataFileController(AbstractController):

    def __init__(self, datafile: DataFile, parent: IDataSetController = None):
        super().__init__(model=datafile, parent=parent)
        self.log = logging.getLogger(__name__)

        self.set_datafile(datafile)

        self._bindings = [
            ('addAction', ('Properties', self._properties_dlg)),
            ('addAction', (Icon.OPEN_FOLDER.icon(), 'Show in Explorer',
                           self._launch_explorer))
        ]
        self.update()

    @property
    def uid(self) -> OID:
        try:
            return super().uid
        except AttributeError:
            return None

    @property
    def entity(self) -> DataFile:
        return cast(DataFile, super().entity)

    @property
    def menu(self):  # pragma: no cover
        return self._bindings

    @property
    def group(self):
        return self.entity.group

    def clone(self):
        raise NotImplementedError

    def update(self):
        super().update()
        if self.entity is not None:
            self.setText(self.entity.name)

    def set_datafile(self, datafile: DataFile):
        self._model = datafile
        if datafile is None:
            self.setText("No Data")
            self.setToolTip("No Data")
            self.setData(None, Qt.UserRole)
        else:
            self.setText(datafile.label)
            self.setToolTip("Source path: {!s}".format(datafile.source_path))
            self.setData(datafile, role=Qt.UserRole)
            if self.entity.group is DataType.GRAVITY:
                self.setIcon(Icon.GRAVITY.icon())
            elif self.entity.group is DataType.TRAJECTORY:
                self.setIcon(Icon.TRAJECTORY.icon())

    def _properties_dlg(self):
        if self.entity is None:
            return
        # TODO: Launch dialog to show datafile properties (name, path, data etc)
        data = HDF5Manager.load_data(self.entity, self.get_parent().hdfpath)
        self.log.info(f'\n{data.describe()}')

    def _launch_explorer(self):
        if self.entity is not None:
            show_in_explorer(self.entity.source_path.parent)
