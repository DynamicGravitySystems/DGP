# -*- coding: utf-8 -*-
from PyQt5.QtGui import QStandardItem
from PyQt5.QtWidgets import QMessageBox, QWidget, QInputDialog

from core.models.project import GravityProject


class BaseProjectController(QStandardItem):
    def __init__(self, project: GravityProject):
        super().__init__(project.name)
        self._project = project
        self._active = None

    @property
    def project(self) -> GravityProject:
        return self._project

    @property
    def active_entity(self):
        return self._active

    def set_active(self, entity):
        raise NotImplementedError

    def properties(self):
        print(self.__class__.__name__)

    def add_child(self, child):
        raise NotImplementedError

    def remove_child(self, child, row: int, confirm: bool=True):
        raise NotImplementedError


class StandardProjectContainer(QStandardItem):
    inherit_context = False

    def __init__(self, label: str, icon: str=None, inherit=False, **kwargs):
        super().__init__(label)
        self.inherit_context = inherit
        self.setEditable(False)
        self._attributes = kwargs

    def properties(self):
        print(self.__class__.__name__)


def confirm_action(title: str, message: str, parent: QWidget=None):
    dlg = QMessageBox(QMessageBox.Question, title, message,
                      QMessageBox.Yes | QMessageBox.No, parent=parent)
    dlg.setDefaultButton(QMessageBox.No)
    dlg.exec_()
    return dlg.result() == QMessageBox.Yes


def get_input(title: str, label: str, text: str, parent: QWidget=None):
    new_text, result = QInputDialog.getText(parent, title, label, text=text)
    if result:
        return new_text
    return False


