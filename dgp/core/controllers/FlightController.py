# -*- coding: utf-8 -*-
from typing import Optional, Any, Union

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QIcon, QStandardItemModel

from core.controllers import common
from core.controllers.common import BaseProjectController, StandardProjectContainer
from core.models.flight import Flight, FlightLine, DataFile

from lib.enums import DataTypes


class StandardFlightItem(QStandardItem):
    def __init__(self, label: str, data: Optional[Any] = None, icon: Optional[str] = None,
                 controller: 'FlightController' = None):
        if icon is not None:
            super().__init__(QIcon(icon), label)
        else:
            super().__init__(label)
        self.setText(label)
        self._data = data
        self._controller = controller  # TODO: Is this used, or will it be?
        # self.setData(data, QtDataRoles.UserRole + 1)
        if data is not None:
            self.setToolTip(str(data.uid))
        self.setEditable(False)

    @property
    def menu_bindings(self):
        return [
            ('addAction', ('Delete <%s>' % self.text(), lambda: self.controller.remove_child(self._data, self.row(),
                                                                                             True)))
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
    inherit_context = True

    def __init__(self, flight: Flight,
                 controller: Optional[BaseProjectController]=None):
        """Assemble the view/controller repr from the base flight object."""
        super().__init__(flight.name)
        self.setEditable(False)

        self._flight = flight
        self._project_controller = controller
        self._active = False

        self._flight_lines = StandardProjectContainer("Flight Lines")
        self._data_files = StandardProjectContainer("Data Files")
        self.appendRow(self._flight_lines)
        self.appendRow(self._data_files)

        self._flight_lines_model = QStandardItemModel()
        self._data_files_model = QStandardItemModel()

        for item in self._flight.flight_lines:
            # Distinct Items must be created for the model and the flight_lines container
            # As the parent property is reassigned on appendRow
            self._flight_lines.appendRow(self._wrap_item(item))
            self._flight_lines_model.appendRow(self._wrap_item(item))

        for item in self._flight.data_files:
            self._data_files.appendRow(self._wrap_item(item))
            self._data_files_model.appendRow(self._wrap_item(item))

        self._bindings = [
            ('addAction', ('Set Active', lambda: self.controller.set_active(self))),
            ('addAction', ('Import Gravity',
                           lambda: self.controller.load_data_file(DataTypes.GRAVITY, self._flight))),
            ('addAction', ('Import Trajectory',
                           lambda: self.controller.load_data_file(DataTypes.TRAJECTORY, self._flight))),
            ('addSeparator', ()),
            ('addAction', ('Delete <%s>' % self._flight.name,
                           lambda: self.controller.remove_child(self._flight, self.row(), True))),
            ('addAction', ('Rename Flight', self.set_name))
        ]

    @property
    def entity(self) -> Flight:
        return self._flight

    @property
    def controller(self) -> BaseProjectController:
        return self._project_controller

    @property
    def menu_bindings(self):
        return self._bindings

    def is_active(self):
        return self.controller.active_entity == self

    def properties(self):
        print(self.__class__.__name__)

    def _wrap_item(self, item: Union[FlightLine, DataFile]):
        return StandardFlightItem(str(item), item, controller=self)

    def add_child(self, child: Union[FlightLine, DataFile]):
        self._flight.add_child(child)
        if isinstance(child, FlightLine):
            self._flight_lines.appendRow(self._wrap_item(child))
            self._flight_lines_model.appendRow(self._wrap_item(child))
        elif isinstance(child, DataFile):
            self._data_files.appendRow(self._wrap_item(child))
            self._flight_lines_model.appendRow(self._wrap_item(child))

    def remove_child(self, child: Union[FlightLine, DataFile], row: int, confirm: bool=True) -> None:
        if confirm:
            if not common.confirm_action("Confirm Deletion", "Are you sure you want to delete %s" % str(child)):
                return
        self._flight.remove_child(child)
        if isinstance(child, FlightLine):
            self._flight_lines.removeRow(row)
            self._flight_lines_model.removeRow(row)
        elif isinstance(child, DataFile):
            self._data_files.removeRow(row)
            self._data_files_model.removeRow(row)

    def get_flight_line_model(self):
        """Return a QStandardItemModel containing all Flight-Lines in this flight"""
        return self._flight_lines_model

    def set_name(self):
        name = common.get_input("Set Name", "Enter a new name:", self._flight.name)
        if name:
            self._flight.name = name
            self.setData(name, role=Qt.DisplayRole)

    def __hash__(self):
        return hash(self._flight.uid)
