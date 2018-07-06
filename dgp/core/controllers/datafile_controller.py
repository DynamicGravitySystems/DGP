# -*- coding: utf-8 -*-
import logging
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QIcon, QColor, QBrush

from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import IFlightController
from dgp.core.controllers.controller_mixins import AttributeProxy
from dgp.core.models.data import DataFile


GRAV_ICON = ":/icons/gravity"
GPS_ICON = ":/icons/gps"


class DataFileController(QStandardItem, AttributeProxy):
    def __init__(self, datafile: DataFile, dataset=None):
        super().__init__()
        self._datafile = datafile
        self._dataset = dataset  # type: DataSetController
        self.log = logging.getLogger(__name__)

        if datafile is not None:
            self.setText(self._datafile.label)
            self.setToolTip("Source Path: " + str(self._datafile.source_path))
            self.setData(self._datafile, role=Qt.UserRole)
            if self._datafile.group == 'gravity':
                self.setIcon(QIcon(GRAV_ICON))
            elif self._datafile.group == 'trajectory':
                self.setIcon(QIcon(GPS_ICON))
        else:
            self.setText("No Data")

        self._bindings = [
            ('addAction', ('Describe', self._describe)),
            ('addAction', ('Delete <%s>' % self._datafile, lambda: None))
        ]

    @property
    def uid(self) -> OID:
        return self._datafile.uid

    @property
    def dataset(self) -> 'DataSetController':
        return self._dataset

    @property
    def menu_bindings(self):
        return self._bindings

    @property
    def data_group(self):
        return self._datafile.group

    @property
    def datamodel(self) -> object:
        return self._datafile

    def _describe(self):
        pass
        # df = self.flight.load_data(self)
        # self.log.debug(df.describe())

