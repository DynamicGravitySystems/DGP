# -*- coding: utf-8 -*-
import itertools
import logging
from typing import Optional, Union, Any, Generator

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from pandas import DataFrame

from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import IAirborneController, IFlightController
from dgp.core.controllers.datafile_controller import DataFileController
from dgp.core.controllers.flightline_controller import FlightLineController
from dgp.core.controllers.gravimeter_controller import GravimeterController
from dgp.core.models.data import DataFile
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
    inherit_context = True

    def __init__(self, flight: Flight, parent: IAirborneController = None):
        """Assemble the view/controller repr from the base flight object."""
        super().__init__()
        self.log = logging.getLogger(__name__)
        self._flight = flight
        self._parent = parent
        self.setData(flight, Qt.UserRole)
        self.setEditable(False)

        self._active = False

        self._flight_lines = ProjectFolder("Flight Lines", FOLDER_ICON)
        self._data_files = ProjectFolder("Data Files", FOLDER_ICON)
        self._sensors = ProjectFolder("Sensors", FOLDER_ICON)
        self.appendRow(self._flight_lines)
        self.appendRow(self._data_files)
        self.appendRow(self._sensors)

        self._control_map = {FlightLine: FlightLineController,
                             DataFile: DataFileController,
                             Gravimeter: GravimeterController}
        self._child_map = {FlightLine: self._flight_lines,
                           DataFile: self._data_files,
                           Gravimeter: self._sensors}

        self._data_model = QStandardItemModel()

        for line in self._flight.flight_lines:
            self._flight_lines.appendRow(FlightLineController(line, self))

        for file in self._flight.data_files:  # type: DataFile
            self._data_files.appendRow(DataFileController(file, self))

        self._active_gravity = None  # type: DataFileController
        self._active_trajectory = None  # type: DataFileController

        # Set the first available gravity/trajectory file to active
        for file_ctrl in self._data_files.items():  # type: DataFileController
            if self._active_gravity is None and file_ctrl.data_group == 'gravity':
                self.set_active_child(file_ctrl)
            if self._active_trajectory is None and file_ctrl.data_group == 'trajectory':
                self.set_active_child(file_ctrl)

        # TODO: Consider adding MenuPrototype class which could provide the means to build QMenu
        self._bindings = [  # pragma: no cover
            ('addAction', ('Set Active', lambda: self.get_parent().set_active_child(self))),
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
    def proxied(self) -> object:
        return self._flight

    @property
    def data_model(self) -> QStandardItemModel:
        """Return the data model representing each active Data channel in the flight"""
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

    @property
    def gravity(self):
        if not self._active_gravity:  # pragma: no cover
            self.log.warning("No gravity file is set to active state.")
            return None
        return self._active_gravity.get_data()

    @property
    def trajectory(self):
        if self._active_trajectory is None:  # pragma: no cover
            self.log.warning("No trajectory file is set to active state.")
            return None
        return self._active_trajectory.get_data()

    @property
    def lines_model(self) -> QStandardItemModel:
        """
        Returns the :obj:`QStandardItemModel` of FlightLine wrapper objects
        """
        return self._flight_lines.internal_model

    @property
    def lines(self) -> Generator[FlightLine, None, None]:
        for line in self._flight.flight_lines:
            yield line

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
    def set_active_child(self, child: DataFileController, emit: bool = True):
        if not isinstance(child, DataFileController):
            raise TypeError("Child {0!r} cannot be set to active (invalid type)".format(child))
        try:
            df = self.load_data(child)
        except LoadError:
            self.log.exception("Error loading DataFile")
            return

        for i in range(self._data_files.rowCount()):
            ci = self._data_files.child(i, 0)  # type: DataFileController
            if ci.data_group == child.data_group:
                ci.set_inactive()

        self.data_model.clear()
        if child.data_group == 'gravity':
            self._active_gravity = child
            child.set_active()

            # Experimental work on channel model
            # TODO: Need a way to clear ONLY the appropriate channels from the model, not all
            # e.g. don't clear trajectory channels when gravity file is changed

            for col in df:
                channel = QStandardItem(col)
                channel.setData(df[col], Qt.UserRole)
                channel.setCheckable(True)
                self._data_model.appendRow([channel, QStandardItem("Plot1"), QStandardItem("Plot2")])

        # TODO: Implement and add test coverage
        elif child.data_group == 'trajectory':  # pragma: no cover
            self._active_trajectory = child
            child.set_active()

    def get_active_child(self):
        # TODO: Implement and add test coverage
        pass

    def add_child(self, child: Union[FlightLine, DataFile]) -> Union[FlightLineController, DataFileController]:
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
        for item in itertools.chain(self._flight_lines.items(),  # pragma: no branch
                                    self._data_files.items()):
            if item.uid == uid:
                return item

    def load_data(self, datafile: DataFileController) -> DataFrame:
        if self.get_parent() is None:
            raise LoadError("Flight has no parent or HDF Controller")
        try:
            return self.get_parent().hdf5store.load_data(datafile.data(Qt.UserRole))
        except OSError as e:
            raise LoadError from e

    def set_name(self):  # pragma: no cover
        name = helpers.get_input("Set Name", "Enter a new name:", self._flight.name)
        if name:
            self.set_attr('name', name)

    def __hash__(self):
        return hash(self._flight.uid)

    def __str__(self):
        return str(self._flight)
