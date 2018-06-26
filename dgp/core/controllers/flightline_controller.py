# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QIcon

from dgp.core.controllers.controller_interfaces import IBaseController
from dgp.core.controllers.controller_mixins import PropertiesProxy
from dgp.core.models.flight import FlightLine


class FlightLineController(QStandardItem, PropertiesProxy):

    def __init__(self, flightline: FlightLine, controller: IBaseController):
        super().__init__()
        self._flightline = flightline
        self._controller: IBaseController = controller
        self.setData(flightline, Qt.UserRole)
        self.setText(str(self._flightline))
        self.setIcon(QIcon(":/icons/AutosizeStretch_16x.png"))

    @property
    def proxied(self) -> FlightLine:
        return self._flightline

    def update_line(self, start, stop):
        self._flightline.start = start
        self._flightline.stop = stop
        self.setText(str(self._flightline))

