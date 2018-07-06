# -*- coding: utf-8 -*-
import itertools
import logging
from pathlib import Path
from typing import Optional, Union, Any, Generator

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from pandas import DataFrame

from dgp.core.controllers.dataset_controller import DataSetController
from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import IAirborneController, IFlightController
from dgp.core.controllers.datafile_controller import DataFileController
from dgp.core.controllers.flightline_controller import FlightLineController
from dgp.core.controllers.gravimeter_controller import GravimeterController
from dgp.core.models.data import DataFile
from dgp.core.models.dataset import DataSet
from dgp.core.models.flight import Flight, FlightLine
from dgp.core.models.meter import Gravimeter
from dgp.core.types.enumerations import DataTypes
from dgp.gui.dialogs.add_flight_dialog import AddFlightDialog
from . import controller_helpers as helpers
from .project_containers import ProjectFolder

FOLDER_ICON = ":/icons/folder_open.png"


class LoadError(Exception):
    pass


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
    """

    @property
    def hdf5path(self) -> Path:
        return self._parent.hdf5store

    inherit_context = True

    def __init__(self, flight: Flight, parent: IAirborneController = None):
        """Assemble the view/controller repr from the base flight object."""
        super().__init__()
        self.log = logging.getLogger(__name__)
        self._flight = flight
        self._parent = parent
        self.setData(flight, Qt.UserRole)
        self.setEditable(False)

        self._datasets = ProjectFolder("Datasets", FOLDER_ICON)
        self._active_dataset: DataSetController = None

        self._sensors = ProjectFolder("Sensors", FOLDER_ICON)
        self.appendRow(self._datasets)
        self.appendRow(self._sensors)

        self._control_map = {DataSet: DataSetController,
                             Gravimeter: GravimeterController}
        self._child_map = {DataSet: self._datasets,
                           Gravimeter: self._sensors}

        self._data_model = QStandardItemModel()
        # TODO: How to keep this synced?
        self._dataset_model = QStandardItemModel()

        for dataset in self._flight._datasets:
            control = DataSetController(dataset, self)
            self._datasets.appendRow(control)
            if dataset._active:
                self.set_active_dataset(control)

        # TODO: Consider adding MenuPrototype class which could provide the means to build QMenu
        self._bindings = [  # pragma: no cover
            ('addAction', ('Add Dataset', lambda: None)),
            ('addAction', ('Set Active',
                           lambda: self.get_parent().set_active_child(self))),
            # TODO: Move these actions to Dataset controller?
            ('addAction', ('Import Gravity',
                           lambda: self.get_parent().load_file_dlg(DataTypes.GRAVITY, self))),
            ('addAction', ('Import Trajectory',
                           lambda: self.get_parent().load_file_dlg(DataTypes.TRAJECTORY, self))),
            ('addSeparator', ()),
            ('addAction', ('Delete <%s>' % self._flight.name,
                           lambda: self.get_parent().remove_child(self._flight, self.row(), True))),
            ('addAction', ('Rename Flight', lambda: self.set_name())),
            ('addAction', ('Properties',
                           lambda: AddFlightDialog.from_existing(self, self.get_parent()).exec_()))
        ]

        self.update()

    @property
    def uid(self) -> OID:
        return self._flight.uid

    @property
    def datamodel(self) -> object:
        return self._flight

    # TODO: Rename this (maybe deprecated with DataSets)
    @property
    def data_model(self) -> QStandardItemModel:
        """Return the data model representing each active Data channel in
        the flight
        """
        return self._data_model

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

    def get_parent(self) -> IAirborneController:
        return self._parent

    def set_parent(self, parent: IAirborneController) -> None:
        self._parent = parent

    def update(self):
        self.setText(self._flight.name)
        self.setToolTip(str(self._flight.uid))

    def clone(self):
        return FlightController(self._flight, parent=self.get_parent())

    def is_active(self):
        return self.get_parent().get_active_child() == self

    # TODO: This is not fully implemented
    def set_active_dataset(self, dataset: DataSetController,
                           emit: bool = True):
        if not isinstance(dataset, DataSetController):
            raise TypeError("Child {0!r} cannot be set to active (invalid type)".format(dataset))
        dataset.set_active(True)
        self._active_dataset = dataset

    def get_active_child(self):
        # TODO: Implement and add test coverage
        return self._active_dataset

    def add_child(self, child: DataSet) -> DataSetController:
        """Adds a child to the underlying Flight, and to the model representation
        for the appropriate child type.

        Parameters
        ----------
        child : Union[:obj:`FlightLine`, :obj:`DataFile`]
            The child model instance - either a FlightLine or DataFile

        Returns
        -------
        Union[:obj:`FlightLineController`, :obj:`DataFileController`]
            Returns a reference to the controller encapsulating the added child

        Raises
        ------
        :exc:`TypeError`
            if child is not a :obj:`FlightLine` or :obj:`DataFile`

        """
        child_key = type(child)
        if child_key not in self._control_map:
            raise TypeError("Invalid child type {0!s} supplied".format(child_key))

        self._flight.add_child(child)
        control = self._control_map[child_key](child, self)
        self._child_map[child_key].appendRow(control)
        return control

    def remove_child(self, child: Union[FlightLine, DataFile], row: int, confirm: bool = True) -> bool:
        """
        Remove the specified child primitive from the underlying :obj:`~dgp.core.models.flight.Flight`
        and from the respective model representation within the FlightController

        Parameters
        ----------
        child : Union[:obj:`~dgp.core.models.flight.FlightLine`, :obj:`~dgp.core.models.data.DataFile`]
            The child model object to be removed
        row : int
            The row number of the child's controller wrapper
        confirm : bool, optional
            If True spawn a confirmation dialog requiring user input to confirm removal

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
        if type(child) not in self._control_map:
            raise TypeError("Invalid child type supplied")
        if confirm:  # pragma: no cover
            if not helpers.confirm_action("Confirm Deletion",
                                          "Are you sure you want to delete %s" % str(child),
                                          self.get_parent().get_parent()):
                return False

        self._flight.remove_child(child)
        self._child_map[type(child)].removeRow(row)
        return True

    def get_child(self, uid: Union[str, OID]) -> Union[FlightLineController, DataFileController, None]:
        """Retrieve a child controller by UIU
        A string base_uuid can be passed, or an :obj:`OID` object for comparison
        """
        # TODO: Should this also search datafiles?
        for item in self._datasets.items():
            if item.uid == uid:
                return item

    def set_name(self):  # pragma: no cover
        name = helpers.get_input("Set Name", "Enter a new name:", self._flight.name)
        if name:
            self.set_attr('name', name)

    def __hash__(self):
        return hash(self._flight.uid)

    def __str__(self):
        return str(self._flight)
