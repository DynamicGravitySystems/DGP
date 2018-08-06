# -*- coding: utf-8 -*-
import logging
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import IDataSetController
from dgp.core.controllers.controller_interfaces import IFlightController
from dgp.core.controllers.controller_mixins import AttributeProxy
from dgp.core.types.enumerations import Icon
from dgp.core.controllers.controller_helpers import show_in_explorer
from dgp.core.models.datafile import DataFile


class DataFileController(QStandardItem, AttributeProxy):
    def __init__(self, datafile: DataFile, dataset=None):
        super().__init__()
        self._datafile = datafile
        self._dataset = dataset  # type: IDataSetController
        self.log = logging.getLogger(__name__)

        self.set_datafile(datafile)

        self._bindings = [
            ('addAction', ('Describe', self._describe)),
            # ('addAction', ('Delete <%s>' % self._datafile, lambda: None))
            ('addAction', (QIcon(Icon.OPEN_FOLDER.value), 'Show in Explorer',
                           self._launch_explorer))
        ]

    @property
    def uid(self) -> OID:
        return self._datafile.uid

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
            if self._datafile.group == 'gravity':
                self.setIcon(QIcon(Icon.GRAVITY.value))
            elif self._datafile.group == 'trajectory':
                self.setIcon(QIcon(Icon.TRAJECTORY.value))

    def _describe(self):
        pass
        # df = self.flight.load_data(self)
        # self.log.debug(df.describe())

    def _launch_explorer(self):
        if self._datafile is not None:
            show_in_explorer(self._datafile.source_path.parent)
