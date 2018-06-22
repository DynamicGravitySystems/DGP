# -*- coding: utf-8 -*-
from typing import Optional, Any, Union

from PyQt5.QtGui import QStandardItem, QIcon

from core.controllers.common import StandardProjectContainer
from core.models.flight import Flight, FlightLine, DataFile

from gui.qtenum import QtDataRoles
from lib.enums import DataTypes


class StandardFlightItem(QStandardItem):
    def __init__(self, label: str, data: Optional[Any] = None, icon: Optional[str] = None,
                 controller: 'FlightController' = None):
        if icon is not None:
            super().__init__(QIcon(icon), label)
        else:
            super().__init__(label)
        self._data = data
        self._controller = controller  # TODO: Is this used, or will it be?
        self.setData(data, QtDataRoles.UserRole)
        if data is not None:
            self.setToolTip(str(data.uid))
        self.setEditable(False)

    @property
    def menu_bindings(self):
        return [
            ('addAction', ('Delete <%s>' % self.text(), lambda: self.controller.remove_child(self._data, self.row())))
        ]

    @property
    def uid(self):
        return self._data.uid

    @property
    def controller(self) -> 'FlightController':
        return self._controller

    def properties(self):
        print(self.__class__.__name__)


class FlightController(QStandardItem):
    def __init__(self, flight: Flight,
                 controller: Optional[Union['ProjectController', 'AirborneController']]=None):
        """Assemble the view/controller repr from the base flight object."""
        super().__init__(flight.name)
        self.setEditable(False)

        self._flight = flight
        self._project_controller = controller

        self._flight_lines = StandardProjectContainer("Flight Lines")
        self._data_files = StandardProjectContainer("Data Files")
        self.appendRow(self._flight_lines)
        self.appendRow(self._data_files)

        for line in self._flight.flight_lines:
            self._flight_lines.appendRow(StandardFlightItem(str(line), line, ':/icons/plane_icon.png', controller=self))

        for file in self._flight.data_files:
            self._data_files.appendRow(StandardFlightItem(str(file), file, controller=self))

        self._bindings = [
            # ('addAction', (section_header,)),
            ('addAction', ('Import Gravity',
                           lambda: self.controller.load_data_file(DataTypes.GRAVITY, self._flight))),
            ('addAction', ('Import Trajectory',
                           lambda: self.controller.load_data_file(DataTypes.TRAJECTORY, self._flight))),
            ('addSeparator', ()),
            ('addAction', ('Delete <%s>' % self._flight.name,
                           lambda: self.controller.remove_child(self._flight, self.row())))
        ]

    @property
    def controller(self):
        return self._project_controller

    @property
    def menu_bindings(self):
        return self._bindings

    def properties(self):
        print(self.__class__.__name__)

    def add_child(self, child: Union[FlightLine, DataFile]):
        item = StandardFlightItem(str(child), child, controller=self)
        self._flight.add_child(child)
        if isinstance(child, FlightLine):
            self._flight_lines.appendRow(item)
        elif isinstance(child, DataFile):
            self._data_files.appendRow(item)

    def remove_child(self, child: Union[FlightLine, DataFile], row: int) -> None:
        self._flight.remove_child(child)
        if isinstance(child, FlightLine):
            self._flight_lines.removeRow(row)
        elif isinstance(child, DataFile):
            self._data_files.removeRow(row)
