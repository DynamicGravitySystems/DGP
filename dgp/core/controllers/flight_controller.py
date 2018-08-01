# -*- coding: utf-8 -*-
import itertools
import logging
from _weakrefset import WeakSet
from pathlib import Path
from typing import Optional, Union, Any, Generator

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QWidget
from pandas import DataFrame

from dgp.core.controllers.dataset_controller import DataSetController
from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import IAirborneController, IFlightController
from dgp.core.controllers.gravimeter_controller import GravimeterController
from dgp.core.models.dataset import DataSet
from dgp.core.models.flight import Flight
from dgp.core.models.meter import Gravimeter
from dgp.core.types.enumerations import DataTypes
from dgp.gui.dialogs.add_flight_dialog import AddFlightDialog
from . import controller_helpers as helpers


class FlightController(IFlightController):
    """
    FlightController is a wrapper around :obj:`Flight` objects, and provides
    a presentation and interaction layer for use of the underlying Flight
    instance.
    All user-space mutations or queries to a Flight object should be proxied
    through a FlightController in order to ensure that the data and presentation
    state is kept synchronized.

    As a child of :obj:`QStandardItem` the FlightController can be directly
    added as a child to another QStandardItem, or as a row/child in a
    :obj:`QAbstractItemModel` or :obj:`QStandardItemModel`
    The default display behavior is to provide the Flights Name.
    A :obj:`QIcon` or string path to a resource can be provided for decoration.

    The FlightController class also acts as a proxy to the underlying :obj:`Flight`
    by implementing __getattr__, and allowing access to any @property decorated
    methods of the Flight.

    Parameters
    ----------
    flight : :class:`Flight`
    project : :class:`IAirborneController`, Optional

    """

    inherit_context = True

    def __init__(self, flight: Flight, project: IAirborneController = None):
        """Assemble the view/controller repr from the base flight object."""
        super().__init__()
        self.log = logging.getLogger(__name__)
        self._flight = flight
        self._parent = project
        self._active: bool = False
        self.setData(flight, Qt.UserRole)
        self.setEditable(False)

        self._dataset_model = QStandardItemModel()

        for dataset in self._flight.datasets:
            control = DataSetController(dataset, self)
            self.appendRow(control)
            self._dataset_model.appendRow(control.clone())

        # Add default DataSet if none defined
        if not len(self._flight.datasets):
            self.add_child(DataSet())

        # TODO: Consider adding MenuPrototype class which could provide the means to build QMenu
        self._bindings = [  # pragma: no cover
            ('addAction', ('Add Dataset', self._add_dataset)),
            ('addAction', ('Set Active',
                           lambda: self._activate_self())),
            ('addAction', ('Import Gravity',
                           lambda: self._load_file_dialog(DataTypes.GRAVITY))),
            ('addAction', ('Import Trajectory',
                           lambda: self._load_file_dialog(DataTypes.TRAJECTORY))),
            ('addSeparator', ()),
            ('addAction', (f'Delete {self._flight.name}',
                           lambda: self._delete_self(confirm=True))),
            ('addAction', ('Rename Flight', lambda: self._set_name())),
            ('addAction', ('Properties',
                           lambda: self._show_properties_dlg()))
        ]

        self._clones = WeakSet()

        self.update()

    @property
    def uid(self) -> OID:
        return self._flight.uid

    @property
    def children(self):
        for i in range(self.rowCount()):
            yield self.child(i, 0)

    @property
    def menu_bindings(self):  # pragma: no cover
        """
        Returns
        -------
        List[Tuple[str, Tuple[str, Callable],...]
            A list of tuples declaring the QMenu construction parameters for this
            object.
        """
        return self._bindings

    @property
    def datamodel(self) -> Flight:
        return self._flight

    @property
    def datasets(self) -> QStandardItemModel:
        return self._dataset_model

    @property
    def project(self) -> IAirborneController:
        return self._parent

    def get_parent(self) -> IAirborneController:
        return self._parent

    def set_parent(self, parent: IAirborneController) -> None:
        self._parent = parent

    def update(self):
        self.setText(self._flight.name)
        self.setToolTip(str(self._flight.uid))
        super().update()
        for clone in self._clones:
            clone.update()

    def clone(self):
        clone = FlightController(self._flight, project=self.get_parent())
        self._clones.add(clone)
        return clone

    @property
    def is_active(self):
        return self._active

    def set_active(self, state: bool):
        self._active = bool(state)
        if self._active:
            self.setBackground(QColor('green'))
        else:
            self.setBackground(QColor('white'))

    @property
    def active_child(self) -> DataSetController:
        """active_child overrides method in IParent

        If no child is active, try to activate the first child (row 0) and
        return the newly active child.
        If the flight has no children None will be returned

        """
        child = super().active_child
        if child is None and self.rowCount():
            self.activate_child(self.child(0).uid)
            return self.active_child
        return child

    def add_child(self, child: DataSet) -> DataSetController:
        """Adds a child to the underlying Flight, and to the model representation
        for the appropriate child type.

        Parameters
        ----------
        child : :obj:`DataSet`
            The child model instance - either a FlightLine or DataFile

        Returns
        -------
        :obj:`DataSetController`
            Returns a reference to the controller encapsulating the added child

        Raises
        ------
        :exc:`TypeError`
            if child is not a :obj:`DataSet`

        """
        if not isinstance(child, DataSet):
            raise TypeError(f'Invalid child of type {type(child)} supplied to'
                            f'FlightController, must be {type(DataSet)}')

        self._flight.datasets.append(child)
        control = DataSetController(child, self)
        self.appendRow(control)
        self._dataset_model.appendRow(control.clone())
        return control

    def remove_child(self, uid: Union[OID, str], confirm: bool = True) -> bool:
        """
        Remove the specified child primitive from the underlying
        :obj:`~dgp.core.models.flight.Flight` and from the respective model
        representation within the FlightController

        Parameters
        ----------
        uid : :obj:`OID`
            The child model object to be removed
        confirm : bool, optional
            If True spawn a confirmation dialog requiring user confirmation

        Returns
        -------
        bool
            True if successful
            False if user does not confirm removal action

        Raises
        ------
        :exc:`TypeError`
            if child is not a :obj:`FlightLine` or :obj:`DataFile`

        """
        child = self.get_child(uid)
        if child is None:
            raise KeyError(f'Child with uid {uid!s} not in flight {self!s}')
        if confirm:  # pragma: no cover
            if not helpers.confirm_action("Confirm Deletion",
                                          f'Are you sure you want to delete {child!r}',
                                          self.parent_widget):
                return False

        self._flight.datasets.remove(child.datamodel)
        self._dataset_model.removeRow(child.row())
        self.removeRow(child.row())
        return True

    def get_child(self, uid: Union[OID, str]) -> DataSetController:
        return super().get_child(uid)

    # Menu Action Handlers
    def _activate_self(self):
        self.get_parent().activate_child(self.uid, emit=True)

    def _add_dataset(self):
        self.add_child(DataSet(name=f'DataSet-{self.datasets.rowCount()}'))

    def _delete_self(self, confirm: bool = True):
        self.get_parent().remove_child(self.uid, confirm)

    def _set_name(self):  # pragma: no cover
        name = helpers.get_input("Set Name", "Enter a new name:",
                                 self.get_attr('name'),
                                 parent=self.parent_widget)
        if name:
            self.set_attr('name', name)

    def _load_file_dialog(self, datatype: DataTypes):  # pragma: no cover
        self.get_parent().load_file_dlg(datatype, flight=self)

    def _show_properties_dlg(self):  # pragma: no cover
        AddFlightDialog.from_existing(self, self.get_parent(),
                                      parent=self.parent_widget).exec_()

    def __hash__(self):
        return hash(self._flight.uid)

    def __str__(self):
        return str(self._flight)
