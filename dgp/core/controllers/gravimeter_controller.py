# -*- coding: utf-8 -*-
from typing import cast

from dgp.core import Icon
from dgp.core.controllers.controller_interfaces import IAirborneController, IMeterController
from dgp.core.controllers.controller_helpers import get_input
from dgp.core.models.meter import Gravimeter


class GravimeterController(IMeterController):

    def __init__(self, meter: Gravimeter, project, parent: IAirborneController = None):
        super().__init__(meter, project, parent=parent)
        self.setIcon(Icon.METER.icon())

        self._bindings = [
            ('addAction', ('Delete <%s>' % self.entity.name,
                           (lambda: self.get_parent().remove_child(self.uid, True)))),
            ('addAction', ('Rename', self.set_name_dlg))
        ]

    @property
    def entity(self) -> Gravimeter:
        return cast(Gravimeter, super().entity)

    @property
    def menu(self):
        return self._bindings

    def clone(self):
        clone = GravimeterController(self.entity, self.project)
        self.register_clone(clone)
        return clone

    def update(self):
        self.setText(self.entity.name)
        super().update()

    def set_name_dlg(self):  # pragma: no cover
        name = get_input("Set Name", "Enter a new name:", self.entity.name,
                         self.parent_widget)
        if name:
            self.set_attr('name', name)

