# -*- coding: utf-8 -*-
from typing import Optional

from PyQt5.QtCore import QObject, QModelIndex, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QStandardItemModel

from core.controllers.FlightController import FlightController
from core.controllers.common import BaseProjectController

__all__ = ['ProjectTreeModel']


class ProjectTreeModel(QStandardItemModel):
    """Extension of QStandardItemModel which handles Project/Model specific
    events and defines signals for domain specific actions.

    All signals/events should be connected via the model vs the View itself.
    """
    flight_changed = pyqtSignal(FlightController)

    def __init__(self, root: BaseProjectController, parent: Optional[QObject]=None):
        super().__init__(parent)
        self._root = root
        self.appendRow(self._root)

    @property
    def root_controller(self) -> BaseProjectController:
        return self._root

    @pyqtSlot(QModelIndex, name='on_click')
    def on_click(self, index: QModelIndex):
        pass

    @pyqtSlot(QModelIndex, name='on_double_click')
    def on_double_click(self, index: QModelIndex):
        print("Double click received in model")
        item = self.itemFromIndex(index)
        if isinstance(item, FlightController):
            self.root_controller.set_active(item)
