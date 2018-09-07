# -*- coding: utf-8 -*-
from typing import Generator

from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon

from dgp.core import Icon
from dgp.core.controllers.controller_interfaces import AbstractController


class ProjectFolder(QStandardItem):
    """Displayable StandardItem used for grouping sub-elements.
    An internal QStandardItemModel representation is maintained for use in
    other Qt elements e.g. a combo-box or list view.

    The ProjectFolder (QStandardItem) appends the source item to itself
    for display in a view, a clone of the item is created and also added to
    an internal QStandardItemModel for

    Notes
    -----
    Overriding object methods like __getitem__ __iter__ etc seems to break
    """

    def __init__(self, label: str, icon: QIcon = None, **kwargs):
        super().__init__(label)
        if icon is None:
            icon = Icon.OPEN_FOLDER.icon()
        self.setIcon(icon)
        self._model = QStandardItemModel()
        self.setEditable(False)
        self._attributes = kwargs

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

    def items(self) -> Generator[AbstractController, None, None]:
        return (self.child(i, 0) for i in range(self.rowCount()))
