# -*- coding: utf-8 -*-
import logging
from typing import Optional, Generator, Union

from PyQt5.QtCore import QObject, QModelIndex, pyqtSignal, QSortFilterProxyModel, Qt
from PyQt5.QtGui import QStandardItemModel

from dgp.core.types.enumerations import DataType
from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import (IFlightController,
                                                        IAirborneController,
                                                        IDataSetController)
from dgp.core.controllers.controller_helpers import confirm_action
from dgp.gui.utils import ProgressEvent

__all__ = ['ProjectTreeModel']


class ProjectTreeModel(QStandardItemModel):
    """Extension of QStandardItemModel which handles Project/Model specific
    events and defines signals for domain specific actions.

    All signals/events should be connected via the model vs the View itself.

    Parameters
    ----------
    project : IAirborneController
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

    Notes
    -----
    ProjectTreeModel loosely conforms to the IParent interface, and uses method
    names reflecting the projects that it contains as children.
    Part of the reason for this naming scheme is the conflict of the 'child'
    property defined in IParent with the child() method of QObject (inherited
    by QStandardItemModel).
    So, although the ProjectTreeModel tries to conform with the overall parent
    interface model, the relationship between Projects and the TreeModel is
    special.

    """
    activeProjectChanged = pyqtSignal(str)
    projectMutated = pyqtSignal()
    projectClosed = pyqtSignal(OID)
    tabOpenRequested = pyqtSignal(OID, object, str)
    tabCloseRequested = pyqtSignal(OID)
    progressNotificationRequested = pyqtSignal(ProgressEvent)

    def __init__(self, project: IAirborneController = None,
                 parent: Optional[QObject] = None):
        super().__init__(parent)
        self.log = logging.getLogger(__name__)
        if project is not None:
            self.appendRow(project)
            project.set_active(True)

    @property
    def active_project(self) -> Union[IAirborneController, None]:
        """Return the active project, if no projects are active then activate
        and return the next project which is a child of the model.

        Returns
        -------
        IAirborneController or None
            The first project controller where is_active is True
            If no projects exist in the model None will be returned instead
        """
        active = next((prj for prj in self.projects if prj.is_active), None)
        if active is None:
            try:
                active = next(self.projects)
                active.set_active(True)
                self.activeProjectChanged.emit(active.get_attr('name'))
                return active
            except StopIteration:
                return None
        else:
            return active

    @property
    def projects(self) -> Generator[IAirborneController, None, None]:
        for i in range(self.rowCount()):
            yield self.item(i, 0)

    def add_project(self, child: IAirborneController):
        self.appendRow(child)

    def remove_project(self, child: IAirborneController, confirm: bool = True) -> None:
        if confirm and not confirm_action("Confirm Project Close",
                                          f"Close Project "
                                          f"{child.get_attr('name')}?",
                                          self.parent()):
            return
        for i in range(child.flight_model.rowCount()):
            flt: IFlightController = child.flight_model.item(i, 0)
            self.tabCloseRequested.emit(flt.uid)
        child.save()
        self.removeRow(child.row())
        self.projectClosed.emit(child.uid)

    def close_flight(self, flight: IFlightController):
        self.tabCloseRequested.emit(flight.uid)

    def notify_tab_changed(self, flight: IFlightController):
        flight.get_parent().activate_child(flight.uid)

    def item_selected(self, index: QModelIndex):
        """Single-click handler for View events"""
        pass

    def item_activated(self, index: QModelIndex):
        """Double-click handler for View events"""

        item = self.itemFromIndex(index)
        if isinstance(item, IDataSetController):
            flt_name = item.get_parent().get_attr('name')
            label = f'{item.get_attr("name")} [{flt_name}]'
            self.tabOpenRequested.emit(item.uid, item, label)
        elif isinstance(item, IAirborneController):
            for project in self.projects:
                if project is item:
                    project.set_active(True)
                else:
                    project.set_active(False)
            self.activeProjectChanged.emit(item.get_attr('name'))
            self.tabOpenRequested.emit(item.uid, item, item.get_attr('name'))
        elif isinstance(item, IFlightController):
            self.tabOpenRequested.emit(item.uid, item, item.get_attr('name'))

    def project_mutated(self, project: IAirborneController):
        self.projectMutated.emit()

    def save_projects(self):
        for i in range(self.rowCount()):
            prj: IAirborneController = self.item(i, 0)
            prj.save()

    def import_gps(self):  # pragma: no cover
        if self.active_project is None:
            return self._warn_no_active_project()
        self.active_project.load_file_dlg(DataType.TRAJECTORY)

    def import_gravity(self):  # pragma: no cover
        if self.active_project is None:
            return self._warn_no_active_project()
        self.active_project.load_file_dlg(DataType.GRAVITY)

    def add_gravimeter(self):  # pragma: no cover
        if self.active_project is None:
            return self._warn_no_active_project()
        self.active_project.add_gravimeter_dlg()

    def add_flight(self):  # pragma: no cover
        if self.active_project is None:
            return self._warn_no_active_project()
        self.active_project.add_flight_dlg()

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
