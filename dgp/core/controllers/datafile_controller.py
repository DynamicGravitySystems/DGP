# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QIcon, QColor, QBrush

from dgp.core.controllers.controller_interfaces import IFlightController
from dgp.core.controllers.controller_mixins import PropertiesProxy
from dgp.core.models.data import DataFile


GRAV_ICON = ":/icons/gravity"
GPS_ICON = ":/icons/gps"


class DataFileController(QStandardItem, PropertiesProxy):
    def __init__(self, datafile: DataFile, controller: IFlightController):
        super().__init__()
        self._datafile = datafile
        self._controller: IFlightController = controller
        self.setText(self._datafile.label)
        self.setToolTip("Source Path: " + str(self._datafile.source_path))
        self.setData(self._datafile, role=Qt.UserRole)
        if self._datafile.group == 'gravity':
            self.setIcon(QIcon(GRAV_ICON))
        elif self._datafile.group == 'trajectory':
            self.setIcon(QIcon(GPS_ICON))

        self._bindings = [
            ('addAction', ('Delete <%s>' % self._datafile,
                           lambda: self._controller.remove_child(self._datafile, self.row()))),
            ('addAction', ('Set Active', self._activate))
        ]

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
        self._controller.set_active_child(self)

    def set_active(self):
        self.setBackground(QBrush(QColor("#85acea")))

    def set_inactive(self):
        self.setBackground(QBrush(QColor("white")))
