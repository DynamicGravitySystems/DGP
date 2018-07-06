# -*- coding: utf-8 -*-
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QIcon

from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import IFlightController
from dgp.core.controllers.controller_mixins import AttributeProxy
from dgp.core.models.flight import FlightLine


class FlightLineController(QStandardItem, AttributeProxy):

    def __init__(self, flightline: FlightLine, controller: IFlightController):
        super().__init__()
        self._flightline = flightline
        self._flight_ctrl = controller
        self.setData(flightline, Qt.UserRole)
        self.setText(str(self._flightline))
        self.setIcon(QIcon(":/icons/AutosizeStretch_16x.png"))

    @property
    def uid(self) -> OID:
        return self._flightline.uid

    @property
    def flight(self) -> IFlightController:
        return self._flight_ctrl

    @property
    def proxied(self) -> FlightLine:
        return self._flightline

    def update_line(self, start, stop, label: Optional[str] = None):
        self._flightline.start = start
        self._flightline.stop = stop
        self._flightline.label = label
        self.setText(str(self._flightline))

