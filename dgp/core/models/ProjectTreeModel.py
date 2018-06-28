# -*- coding: utf-8 -*-
from typing import Optional

from PyQt5.QtCore import QObject, QModelIndex, pyqtSignal, pyqtSlot, QSortFilterProxyModel, Qt
from PyQt5.QtGui import QStandardItemModel

from dgp.core.controllers.flight_controller import FlightController
from dgp.core.controllers.project_controllers import AirborneProjectController

__all__ = ['ProjectTreeModel']


class ProjectTreeModel(QStandardItemModel):
    """Extension of QStandardItemModel which handles Project/Model specific
    events and defines signals for domain specific actions.

    All signals/events should be connected via the model vs the View itself.
    """
    flight_changed = pyqtSignal(FlightController)
    # Fired on any project mutation - can be used to autosave
    project_changed = pyqtSignal()

    def __init__(self, root: AirborneProjectController, parent: Optional[QObject]=None):
        super().__init__(parent)
        self._root = root
        self.appendRow(self._root)

    @property
    def root_controller(self) -> AirborneProjectController:
        return self._root

    @pyqtSlot(QModelIndex, name='on_click')
    def on_click(self, index: QModelIndex):
        pass

    @pyqtSlot(QModelIndex, name='on_double_click')
    def on_double_click(self, index: QModelIndex):
        item = self.itemFromIndex(index)
        if isinstance(item, FlightController):
            self.root_controller.set_active_child(item)
