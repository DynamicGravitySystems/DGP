# -*- coding: utf-8 -*-
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon


class ProjectFolder(QStandardItem):
    """Displayable StandardItem used for grouping sub-elements.
    An internal QStandardItemModel representation is maintained for use in
    other Qt elements e.g. a combo-box or list view.

    The ProjectFolder (QStandardItem) appends the source item to itself
    for display in a view, a clone of the item is created and also added to
    an internal QStandardItemModel for
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

    def __iter__(self):
        pass

