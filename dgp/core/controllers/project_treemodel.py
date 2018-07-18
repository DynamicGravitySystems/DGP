# -*- coding: utf-8 -*-
from typing import Optional

from PyQt5.QtCore import QObject, QModelIndex, pyqtSignal, pyqtSlot, QSortFilterProxyModel, Qt
from PyQt5.QtGui import QStandardItemModel

from dgp.core.controllers.controller_interfaces import IFlightController
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.gui.utils import ProgressEvent

__all__ = ['ProjectTreeModel']


class ProjectTreeModel(QStandardItemModel):
    """Extension of QStandardItemModel which handles Project/Model specific
    events and defines signals for domain specific actions.

    All signals/events should be connected via the model vs the View itself.

    Parameters
    ----------
    project : AirborneProjectController
    parent : QObject, optional

    Attributes
    ----------
    projectMutated : pyqtSignal[]
        Signal emitted to notify application that project data has changed.
    tabOpenRequested : pyqtSignal[IFlightController]
        Signal emitted to request a tab be opened for the supplied Flight
    tabCloseRequested : pyqtSignal(IFlightController)
        Signal notifying application that tab for given flight should be closed
        This is called for example when a Flight is deleted to ensure any open
        tabs referencing it are also deleted.
    progressNotificationRequested : pyqtSignal[ProgressEvent]
        Signal emitted to request a QProgressDialog from the main window.
        ProgressEvent is passed defining the parameters for the progress bar
    progressUpdateRequested : pyqtSignal[ProgressEvent]
        Signal emitted to update an active QProgressDialog
        ProgressEvent must reference an event already emitted by
        progressNotificationRequested

    """
    projectMutated = pyqtSignal()
    tabOpenRequested = pyqtSignal(IFlightController)
    tabCloseRequested = pyqtSignal(IFlightController)
    progressNotificationRequested = pyqtSignal(ProgressEvent)
    progressUpdateRequested = pyqtSignal(ProgressEvent)

    def __init__(self, project: AirborneProjectController, parent: Optional[QObject]=None):
        super().__init__(parent)
        self.appendRow(project)

    def active_changed(self, flight: IFlightController):
        self.tabOpenRequested.emit(flight)

    def close_flight(self, flight: IFlightController):
        self.tabCloseRequested.emit(flight)

    def notify_tab_changed(self, flight: IFlightController):
        flight.get_parent().set_active_child(flight, emit=False)

    def item_selected(self, index: QModelIndex):
        pass

    def item_activated(self, index: QModelIndex):
        item = self.itemFromIndex(index)
        if isinstance(item, IFlightController):
            item.get_parent().set_active_child(item, emit=False)
            self.active_changed(item)

    @pyqtSlot(QModelIndex, name='on_click')
    def on_click(self, index: QModelIndex):  # pragma: no cover
        pass

    @pyqtSlot(QModelIndex, name='on_double_click')
    def on_double_click(self, index: QModelIndex):
        item = self.itemFromIndex(index)
        if isinstance(item, IFlightController):
            item.get_parent().set_active_child(item, emit=False)
            self.active_changed(item)


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



