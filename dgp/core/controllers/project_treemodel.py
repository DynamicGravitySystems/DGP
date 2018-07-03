# -*- coding: utf-8 -*-
from typing import Optional

from PyQt5.QtCore import QObject, QModelIndex, pyqtSignal, pyqtSlot, QSortFilterProxyModel, Qt
from PyQt5.QtGui import QStandardItemModel

from dgp.core.controllers.controller_interfaces import IFlightController, IAirborneController
from dgp.core.controllers.project_controllers import AirborneProjectController

__all__ = ['ProjectTreeModel']


class ProjectTreeModel(QStandardItemModel):
    """Extension of QStandardItemModel which handles Project/Model specific
    events and defines signals for domain specific actions.

    All signals/events should be connected via the model vs the View itself.
    """
    flight_changed = pyqtSignal(IFlightController)
    # Fired on any project mutation - can be used to autosave
    project_changed = pyqtSignal()

    def __init__(self, project: AirborneProjectController, parent: Optional[QObject]=None):
        super().__init__(parent)
        self.appendRow(project)

    @pyqtSlot(QModelIndex, name='on_click')
    def on_click(self, index: QModelIndex):  # pragma: no cover
        pass

    @pyqtSlot(QModelIndex, name='on_double_click')
    def on_double_click(self, index: QModelIndex):
        item = self.itemFromIndex(index)
        if isinstance(item, IFlightController):
            item.get_parent().set_active_child(item)


# Experiment
class ProjectTreeProxyModel(QSortFilterProxyModel):  # pragma: no cover
    """Experiment to filter tree model to a subset - not working currently, may require
    more detailed custom implementation of QAbstractProxyModel
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_type = None
        self.setRecursiveFilteringEnabled(True)

    def setFilterType(self, obj: type):
        self._filter_type = obj

    def sourceModel(self) -> QStandardItemModel:
        return super().sourceModel()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex):
        index: QModelIndex = self.sourceModel().index(source_row, 0, source_parent)
        item = self.sourceModel().itemFromIndex(index)
        print(item)
        data = self.sourceModel().data(index, self.filterRole())
        disp = self.sourceModel().data(index, Qt.DisplayRole)

        res = isinstance(data, self._filter_type)
        print("Result is: %s for row %d" % (str(res), source_row))
        print("Row display value: " + str(disp))

        return res



