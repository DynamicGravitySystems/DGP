# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem

from dgp.core.controllers.controller_interfaces import IAirborneController
from dgp.core.controllers.controller_helpers import get_input
from dgp.core.controllers.controller_mixins import AttributeProxy
from dgp.core.models.meter import Gravimeter


class GravimeterController(QStandardItem, AttributeProxy):
    def __init__(self, meter: Gravimeter, parent: IAirborneController):
        super().__init__(meter.name)
        self.setEditable(False)
        self.setData(meter, role=Qt.UserRole)

        self._meter: Gravimeter = meter
        self._project_controller = parent

        self._bindings = [
            ('addAction', ('Delete <%s>' % self._meter.name,
                           (lambda: self.project.remove_child(self._meter, self.row(), True)))),
            ('addAction', ('Rename', self.set_name))
        ]

    @property
    def project(self) -> IAirborneController:
        return self._project_controller

    @property
    def proxied(self) -> object:
        return self._meter

    @property
    def menu_bindings(self):
        return self._bindings

    def set_name(self):
        name = get_input("Set Name", "Enter a new name:", self._meter.name)
        if name:
            self._meter.name = name
            self.setData(name, role=Qt.DisplayRole)

    def clone(self):
        return GravimeterController(self._meter, self.project)

    def add_child(self, child) -> None:
        raise ValueError("Gravimeter does not support child objects.")

    def remove_child(self, child, row: int) -> None:
        raise ValueError("Gravimeter does not have child objects.")

    def __hash__(self):
        return hash(self._meter.uid)
