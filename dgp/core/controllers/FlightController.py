# -*- coding: utf-8 -*-
from PyQt5.QtCore import QVariant, pyqtSignal, pyqtBoundSignal, QObject
from PyQt5.QtGui import QStandardItem, QIcon

from core.flight import Flight, FlightLine

# This may inherit from a class similar to TreeItem (or directly from same)
from gui.qtenum import QtDataRoles


class CustomItem(QStandardItem):
    def __init__(self, data, label, icon=None, style=None):
        if icon is not None:
            super().__init__(QIcon(icon), label)
        else:
            super().__init__(label)
        self._data = data
        self.setData(data, QtDataRoles.UserRole)


# Look into using QStandardItem either on its own, subclassed, or simply
# as a prototype for improving the AbstractTreeItem used now
# subclassing could mean simply using the QStandardItemModel as well

class FlightController(QStandardItem):

    def __init__(self, flight: Flight):
        """Assemble the view/controller repr from the base flight object.


        We implement BaseTreeItem so that FlightController can be displayed
        within the Project Tree Model


        """
        super().__init__(flight.uid)
        self._flight = flight

        self._flight_lines = QStandardItem("Flight Lines")
        self.appendRow(self._flight_lines)
        for line in self._flight.flight_lines:
            # TODO: Create Line repr
            self._flight_lines.appendRow(QStandardItem(str(line)))

        self._data_files = QStandardItem("Data Files")
        self.appendRow(self._data_files)
        for file in self._flight.data_files:
            self._data_files.appendRow(QStandardItem(str(file)))

    def add_flight_line(self, line: FlightLine) -> None:
        print("Adding line")
        self._flight.add_flight_line(line)
        self._flight_lines.appendRow(QStandardItem(str(line)))

    def add_data_file(self, file: str) -> None:
        pass

