# -*- coding: utf-8 -*-
from typing import Optional, Union

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QIcon, QStandardItemModel

from core.controllers import Containers
from core.controllers.Containers import StandardProjectContainer, StandardFlightItem
from core.controllers.BaseProjectController import BaseProjectController
from core.models.flight import Flight, FlightLine
from core.models.data import DataFile

from core.types.enumerations import DataTypes

FOLDER_ICON = ":/icons/folder_open.png"


class FlightController(QStandardItem):
    inherit_context = True

    def __init__(self, flight: Flight, icon: Optional[str]=None,
                 controller: Optional[BaseProjectController]=None):
        """Assemble the view/controller repr from the base flight object."""
        super().__init__(flight.name)
        if icon is not None:
            self.setIcon(QIcon(icon))
        self.setEditable(False)
        self.setData(flight.uid, Qt.UserRole)

        self._flight = flight
        self._project_controller = controller
        self._active = False

        self._flight_lines = StandardProjectContainer("Flight Lines", FOLDER_ICON)
        self._data_files = StandardProjectContainer("Data Files", FOLDER_ICON)
        self.appendRow(self._flight_lines)
        self.appendRow(self._data_files)

        for item in self._flight.flight_lines:
            self._flight_lines.appendRow(self._wrap_item(item))

        for item in self._flight.data_files:
            self._data_files.appendRow(self._wrap_item(item))

        # Think about multiple files, what to do?
        self._active_gravity = None
        self._active_trajectory = None

        self._bindings = [
            ('addAction', ('Set Active', lambda: self.controller.set_active(self))),
            ('addAction', ('Import Gravity',
                           lambda: self.controller.load_file(DataTypes.GRAVITY, self))),
            ('addAction', ('Import Trajectory',
                           lambda: self.controller.load_file(DataTypes.TRAJECTORY, self))),
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

    @property
    def gravity(self):
        return None

    @property
    def trajectory(self):
        return None

    @property
    def lines_model(self) -> QStandardItemModel:
        return self._flight_lines.internal_model

    def is_active(self):
        return self.controller.active_entity == self

    def properties(self):
        for i in range(self._data_files.rowCount()):
            file = self._data_files.child(i)
            if file._data.group == 'gravity':
                print(file)
                break
        print(self.__class__.__name__)

    def _wrap_item(self, item: Union[FlightLine, DataFile]):
        return StandardFlightItem(str(item), item, controller=self)

    def add_child(self, child: Union[FlightLine, DataFile]):
        self._flight.add_child(child)
        if isinstance(child, FlightLine):
            self._flight_lines.appendRow(self._wrap_item(child))
        elif isinstance(child, DataFile):
            self._data_files.appendRow(self._wrap_item(child))

    def remove_child(self, child: Union[FlightLine, DataFile], row: int, confirm: bool=True) -> None:
        if confirm:
            if not Containers.confirm_action("Confirm Deletion", "Are you sure you want to delete %s" % str(child),
                                             self.controller.get_parent()):
                return
        self._flight.remove_child(child)
        if isinstance(child, FlightLine):
            self._flight_lines.removeRow(row)
        elif isinstance(child, DataFile):
            self._data_files.removeRow(row)

    def set_name(self):
        name = Containers.get_input("Set Name", "Enter a new name:", self._flight.name)
        if name:
            self._flight.name = name
            self.setData(name, role=Qt.DisplayRole)

    def __hash__(self):
        return hash(self._flight.uid)

    def __getattr__(self, key):
        return getattr(self._flight, key)

    def __str__(self):
        return "<Flight: %s :: %s>" % (self._flight.name, repr(self._flight.uid))
