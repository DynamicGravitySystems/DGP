# -*- coding: utf-8 -*-
from typing import Optional, Generator

from PyQt5.QtCore import QObject, QModelIndex, pyqtSignal, QSortFilterProxyModel, Qt
from PyQt5.QtGui import QStandardItemModel

from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import IFlightController, IAirborneController
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
    tabOpenRequested = pyqtSignal(OID, object, str)
    tabCloseRequested = pyqtSignal(OID)
    progressNotificationRequested = pyqtSignal(ProgressEvent)
    progressUpdateRequested = pyqtSignal(ProgressEvent)

    def __init__(self, project: AirborneProjectController, parent: Optional[QObject]=None):
        super().__init__(parent)
        self.appendRow(project)
        self._active = project

    @property
    def active_project(self) -> IAirborneController:
        return self._active

    @property
    def projects(self) -> Generator[IAirborneController, None, None]:
        for i in range(self.rowCount()):
            yield self.item(i, 0)

    def active_changed(self, flight: IFlightController):
        self.tabOpenRequested.emit(flight.uid, flight, flight.get_attr('name'))

    def add_project(self, project: IAirborneController):
        self.appendRow(project)

    def close_flight(self, flight: IFlightController):
        self.tabCloseRequested.emit(flight.uid)

    def notify_tab_changed(self, flight: IFlightController):
        flight.get_parent().set_active_child(flight, emit=False)

    def item_selected(self, index: QModelIndex):
        pass

    def item_activated(self, index: QModelIndex):
        item = self.itemFromIndex(index)
        if isinstance(item, IFlightController):
            item.get_parent().set_active_child(item, emit=False)
            self.active_changed(item)
        elif isinstance(item, IAirborneController):
            self._active = item

    def save_projects(self):
        for i in range(self.rowCount()):
            prj: IAirborneController = self.item(i, 0)
            prj.save()


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



