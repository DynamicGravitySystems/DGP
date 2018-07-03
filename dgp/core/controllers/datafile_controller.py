# -*- coding: utf-8 -*-
import logging
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QIcon, QColor, QBrush

from dgp.core.controllers.controller_interfaces import IFlightController
from dgp.core.controllers.controller_mixins import AttributeProxy
from dgp.core.models.data import DataFile


GRAV_ICON = ":/icons/gravity"
GPS_ICON = ":/icons/gps"


class DataFileController(QStandardItem, AttributeProxy):
    def __init__(self, datafile: DataFile, controller: IFlightController):
        super().__init__()
        self._datafile = datafile
        self._flight_ctrl = controller  # type: IFlightController
        self.log = logging.getLogger(__name__)

        self.setText(self._datafile.label)
        self.setToolTip("Source Path: " + str(self._datafile.source_path))
        self.setData(self._datafile, role=Qt.UserRole)
        if self._datafile.group == 'gravity':
            self.setIcon(QIcon(GRAV_ICON))
        elif self._datafile.group == 'trajectory':
            self.setIcon(QIcon(GPS_ICON))

        self._bindings = [
            ('addAction', ('Set Active', self._activate)),
            ('addAction', ('Describe', self._describe)),
            ('addAction', ('Delete <%s>' % self._datafile,
                           lambda: self.flight.remove_child(self._datafile, self.row())))
        ]

    @property
    def flight(self) -> IFlightController:
        return self._flight_ctrl

    @property
    def menu_bindings(self):
        return self._bindings

    @property
    def data_group(self):
        return self._datafile.group

    @property
    def proxied(self) -> object:
        return self._datafile

    def _activate(self):
        self.flight.set_active_child(self)

    def _describe(self):
        df = self.flight.load_data(self)
        self.log.debug(df.describe())

    def set_active(self):
        self.setBackground(QBrush(QColor("#85acea")))

    def set_inactive(self):
        self.setBackground(QBrush(QColor("white")))

    def get_data(self):
        try:
            return self.flight.load_data(self)
        except IOError:
            return None
