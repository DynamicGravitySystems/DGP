# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Optional, Any

from PyQt5.QtCore import QObject
from PyQt5.QtGui import QStandardItem

from core.controllers.HDFController import HDFController
from core.models.project import GravityProject


class BaseProjectController(QStandardItem):
    def __init__(self, project: GravityProject, parent=None):
        super().__init__(project.name)
        self._project = project
        self._hdfc = HDFController(self._project.path)
        self._active = None
        self._parent = parent

    def get_parent(self) -> QObject:
        return self._parent

    def set_parent(self, value: QObject):
        self._parent = value

    @property
    def name(self) -> str:
        return self.project.name

    @property
    def project(self) -> GravityProject:
        return self._project

    @property
    def path(self) -> Path:
        return self._project.path

    @property
    def active_entity(self):
        return self._active

    @property
    def hdf5store(self) -> HDFController:
        return self._hdfc

    def set_active(self, entity, emit: bool = True):
        raise NotImplementedError

    def properties(self):
        print(self.__class__.__name__)

    def add_child(self, child):
        raise NotImplementedError

    def remove_child(self, child, row: int, confirm: bool=True):
        raise NotImplementedError

    def load_file(self, ftype, destination: Optional[Any]=None) -> None:
        raise NotImplementedError

    def save(self):
        return self.project.to_json(indent=2, to_file=True)

