# -*- coding: utf-8 -*-
from typing import Optional, Any, Union

from PyQt5.QtCore import QObject
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon
from PyQt5.QtWidgets import QMessageBox, QWidget, QInputDialog


class StandardProjectContainer(QStandardItem):
    """Displayable StandardItem used for grouping sub-elements.
    An internal QStandardItemModel representation is maintained for use in
    other Qt elements e.g. a combo-box or list view.
    """
    inherit_context = False

    def __init__(self, label: str, icon: str=None, inherit=False, **kwargs):
        super().__init__(label)
        if icon is not None:
            self.setIcon(QIcon(icon))
        self._model = QStandardItemModel()
        self.inherit_context = inherit
        self.setEditable(False)
        self._attributes = kwargs

    def properties(self):
        print(self.__class__.__name__)

    @property
    def internal_model(self) -> QStandardItemModel:
        return self._model

    def appendRow(self, item: QStandardItem):
        """
        Notes
        -----
        The same item cannot be added to two parents as the parent attribute
        is mutated when added. Use clone() or similar method to create two identical copies.
        """
        super().appendRow(item)
        self._model.appendRow(item.clone())

    def removeRow(self, row: int):
        super().removeRow(row)
        self._model.removeRow(row)


class StandardFlightItem(QStandardItem):
    def __init__(self, label: str, data: Optional[Any] = None, icon: Optional[str] = None,
                 controller: 'FlightController' = None):
        super().__init__(label)
        if icon is not None:
            self.setIcon(QIcon(icon))

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
            ('addAction', ('Delete <%s>' % self.text(),
                           lambda: self.controller.remove_child(self._data, self.row(), True)))
        ]

    @property
    def uid(self):
        return self._data.uid

    @property
    def controller(self) -> 'FlightController':
        return self._controller

    def properties(self):
        print(self.__class__.__name__)


# TODO: Move these into dialog/helpers module
def confirm_action(title: str, message: str,
                   parent: Optional[Union[QWidget, QObject]]=None):
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


