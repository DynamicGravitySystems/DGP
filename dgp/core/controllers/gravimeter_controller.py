# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt

from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import IAirborneController, IMeterController
from dgp.core.controllers.controller_helpers import get_input
from dgp.core.models.meter import Gravimeter


class GravimeterController(IMeterController):

    def __init__(self, meter: Gravimeter, parent: IAirborneController = None):
        super().__init__(meter.name)
        self.setEditable(False)
        self.setData(meter, role=Qt.UserRole)

        self._meter = meter  # type: Gravimeter
        self._parent = parent

        self._bindings = [
            ('addAction', ('Delete <%s>' % self._meter.name,
                           (lambda: self.get_parent().remove_child(self.uid, True)))),
            ('addAction', ('Rename', self.set_name_dlg))
        ]

    @property
    def uid(self) -> OID:
        return self._meter.uid

    @property
    def datamodel(self) -> object:
        return self._meter

    @property
    def menu_bindings(self):
        return self._bindings

    def get_parent(self) -> IAirborneController:
        return self._parent

    def set_parent(self, parent: IAirborneController) -> None:
        self._parent = parent

    def update(self):
        self.setData(self._meter.name, Qt.DisplayRole)

    def set_name_dlg(self):  # pragma: no cover
        name = get_input("Set Name", "Enter a new name:", self._meter.name,
                         self.parent_widget)
        if name:
            self.set_attr('name', name)

    def clone(self):
        return GravimeterController(self._meter, self.get_parent())

    def __hash__(self):
        return hash(self._meter.uid)
