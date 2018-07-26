# -*- coding: utf-8 -*-
import logging
from typing import Optional, Generator

from PyQt5.QtCore import QObject, QModelIndex, pyqtSignal, QSortFilterProxyModel, Qt
from PyQt5.QtGui import QStandardItemModel, QColor

from dgp.core.types.enumerations import DataTypes
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
    activeProjectChanged : pyqtSignal(str)
        Signal emitted to notify application that the active project has changed
        the name of the newly activated project is passed.
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

    """
    activeProjectChanged = pyqtSignal(str)
    projectMutated = pyqtSignal()
    tabOpenRequested = pyqtSignal(OID, object, str)
    tabCloseRequested = pyqtSignal(OID)
    progressNotificationRequested = pyqtSignal(ProgressEvent)

    def __init__(self, project: AirborneProjectController, parent: Optional[QObject]=None):
        super().__init__(parent)
        self.log = logging.getLogger(__name__)
        self.appendRow(project)
        project.setBackground(QColor('green'))
        self._active = project

    @property
    def active_project(self) -> IAirborneController:
        if self._active is None:
            try:
                self._active = next(self.projects)
                self.active_changed(self._active)
            except StopIteration:
                pass
        return self._active

    @property
    def projects(self) -> Generator[IAirborneController, None, None]:
        for i in range(self.rowCount()):
            yield self.item(i, 0)

    def active_changed(self, item):
        if isinstance(item, IFlightController):
            self.tabOpenRequested.emit(item.uid, item, item.get_attr('name'))
        elif isinstance(item, IAirborneController):
            self._active = item
            item.setBackground(QColor('green'))
            self.activeProjectChanged.emit(item.get_attr('name'))

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
        elif isinstance(item, IAirborneController):
            for project in self.projects:
                project.setBackground(QColor('white'))
        self.active_changed(item)

    def save_projects(self):
        for i in range(self.rowCount()):
            prj: IAirborneController = self.item(i, 0)
            prj.save()

    def close_project(self, project: IAirborneController):
        for i in range(project.flight_model.rowCount()):
            flt: IFlightController = project.flight_model.item(i, 0)
            self.tabCloseRequested.emit(flt.uid)
        project.save()
        self.removeRow(project.row())
        try:
            self._active = next(self.projects)
        except StopIteration:
            self._active = None

    def import_gps(self):  # pragma: no cover
        if self.active_project is None:
            return self._warn_no_active_project()
        self._active.load_file_dlg(DataTypes.TRAJECTORY)

    def import_gravity(self):  # pragma: no cover
        if self.active_project is None:
            return self._warn_no_active_project()
        self._active.load_file_dlg(DataTypes.GRAVITY)

    def add_gravimeter(self):  # pragma: no cover
        if self.active_project is None:
            return self._warn_no_active_project()
        self._active.add_gravimeter()

    def add_flight(self):  # pragma: no cover
        if self.active_project is None:
            return self._warn_no_active_project()
        self._active.add_flight()

    def _warn_no_active_project(self):
        self.log.warning("No active projects.")


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
