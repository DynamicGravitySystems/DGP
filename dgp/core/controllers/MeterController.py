# -*- coding: utf-8 -*-
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem

from . import common
from core.models.meter import Gravimeter


class GravimeterController(QStandardItem):
    def __init__(self, meter: Gravimeter,
                 controller: Optional[common.BaseProjectController]=None):
        super().__init__(meter.name)
        self.setEditable(False)

        self._meter = meter
        self._project_controller = controller

        self._bindings = [
            ('addAction', ('Delete <%s>' % self._meter.name,
                           (lambda: self.controller.remove_child(self._meter, self.row(), True)))),
            ('addAction', ('Rename', self.set_name))
        ]

    @property
    def entity(self) -> Gravimeter:
        return self._meter

    @property
    def controller(self) -> common.BaseProjectController:
        return self._project_controller

    @property
    def menu_bindings(self):
        return self._bindings

    def add_child(self, child) -> None:
        pass

    def remove_child(self, child, row: int) -> None:
        pass

    def set_name(self):
        name = common.get_input("Set Name", "Enter a new name:", self._meter.name)
        if name:
            self._meter.name = name
            self.setData(name, role=Qt.DisplayRole)

    def __hash__(self):
        return hash(self._meter.uid)
