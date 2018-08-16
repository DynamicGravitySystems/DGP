# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget

from dgp.core.controllers.flight_controller import FlightController
from dgp.gui.widgets.workspace_widget import WorkspaceTab


class FlightMapTab(QWidget):
    def __init__(self, flight, parent=None):
        super().__init__(parent=parent, flags=Qt.Widget)
        self.flight = flight


class FlightTab(WorkspaceTab):
    def __init__(self, flight: FlightController, parent=None):
        super().__init__(parent=parent, flags=Qt.Widget)
        self.flight = flight
        layout = QtWidgets.QHBoxLayout(self)
        self.workspace = QtWidgets.QTabWidget()
        self.workspace.addTab(FlightMapTab(self.flight), "Flight Map")

        layout.addWidget(self.workspace)

    @property
    def uid(self):
        return self.flight.uid
