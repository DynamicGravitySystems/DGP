# -*- coding: utf-8 -*-
import logging
from typing import Optional, Union, Any

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QIcon, QStandardItemModel

from dgp.core.controllers.controller_interfaces import IAirborneController, IFlightController
from dgp.core.controllers.datafile_controller import DataFileController
from dgp.core.controllers.flightline_controller import FlightLineController
from dgp.core.controllers.controller_mixins import PropertiesProxy
from gui.dialog.add_flight_dialog import AddFlightDialog
from . import controller_helpers as helpers
from .project_containers import ProjectFolder
from dgp.core.models.flight import Flight, FlightLine
from dgp.core.models.data import DataFile

from core.types.enumerations import DataTypes

FOLDER_ICON = ":/icons/folder_open.png"


class FlightController(IFlightController, PropertiesProxy):
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

    def __init__(self, flight: Flight, icon: Optional[str] = None,
                 controller: IAirborneController = None):
        """Assemble the view/controller repr from the base flight object."""
        super().__init__()
        self.log = logging.getLogger(__name__)
        self._flight = flight
        self.setData(flight, Qt.UserRole)
        if icon is not None:
            self.setIcon(QIcon(icon))
        self.setEditable(False)

        self._project_controller = controller
        self._active = False

        self._flight_lines = ProjectFolder("Flight Lines", FOLDER_ICON)
        self._data_files = ProjectFolder("Data Files", FOLDER_ICON)
        self.appendRow(self._flight_lines)
        self.appendRow(self._data_files)

        for line in self._flight.flight_lines:
            self._flight_lines.appendRow(FlightLineController(line, self))

        for file in self._flight.data_files:
            self._data_files.appendRow(DataFileController(file, self))

        # Think about multiple files, what to do?
        self._active_gravity = None
        self._active_trajectory = None

        self._bindings = [
            ('addAction', ('Set Active', lambda: self.controller.set_active_child(self))),
            ('addAction', ('Import Gravity',
                           lambda: self.controller.load_file(DataTypes.GRAVITY))),
            ('addAction', ('Import Trajectory',
                           lambda: self.controller.load_file(DataTypes.TRAJECTORY))),
            ('addSeparator', ()),
            ('addAction', ('Delete <%s>' % self._flight.name,
                           lambda: self.controller.remove_child(self._flight, self.row(), True))),
            ('addAction', ('Rename Flight', lambda: self.set_name(interactive=True))),
            ('addAction', ('Properties',
                           lambda: AddFlightDialog.from_existing(self, self.controller).exec_()))
        ]

        self.update()

    def update(self):
        self.setText(self._flight.name)
        self.setToolTip(str(self._flight.uid))

    def clone(self):
        return FlightController(self._flight, controller=self.controller)

    @property
    def controller(self) -> IAirborneController:
        return self._project_controller

    @property
    def menu_bindings(self):
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
        return None

    @property
    def trajectory(self):
        return None

    @property
    def lines_model(self) -> QStandardItemModel:
        """
        Returns the :obj:`QStandardItemModel` of FlightLine wrapper objects
        """
        return self._flight_lines.internal_model

    def is_active(self):
        return self.controller.get_active_child() == self

    def properties(self):
        for i in range(self._data_files.rowCount()):
            file = self._data_files.child(i)
            if file._data.group == 'gravity':
                print(file)
                break
        print(self.__class__.__name__)

    @property
    def proxied(self) -> object:
        return self._flight

    def set_active_child(self, child: DataFileController, emit: bool = True):
        if not isinstance(child, DataFileController):
            self.log.warning("Invalid child attempted to activate: %s", str(type(child)))
            return

        for i in range(self._data_files.rowCount()):
            ci: DataFileController = self._data_files.child(i, 0)
            if ci.data_group == child.data_group:
                ci.set_inactive()

        print(child.data_group)
        if child.data_group == 'gravity':
            self._active_gravity = child.data(Qt.UserRole)
            child.set_active()
            print("Set gravity child to active")
        if child.data_group == 'trajectory':
            self._active_trajectory = child.data(Qt.UserRole)
            child.set_active()

    def get_active_child(self):
        pass

    def add_child(self, child: Union[FlightLine, DataFile]) -> bool:
        """
        Add a child to the underlying Flight, and to the model representation
        for the appropriate child type.

        Parameters
        ----------
        child: Union[FlightLine, DataFile]
            The child model instance - either a FlightLine or DataFile

        Returns
        -------
        bool: True on successful adding of child,
              False on fail (e.g. child is not instance of FlightLine or DataFile

        """
        self._flight.add_child(child)
        if isinstance(child, FlightLine):
            self._flight_lines.appendRow(FlightLineController(child, self))
        elif isinstance(child, DataFile):
            self._data_files.appendRow(DataFileController(child, self))
        else:
            self.log.warning("Child of type %s could not be added to flight.", str(type(child)))
            return False
        return True

    def remove_child(self, child: Union[FlightLine, DataFile], row: int, confirm: bool = True) -> bool:
        """
        Remove the specified child primitive from the underlying :obj:`Flight`
        and from the respective model representation within the FlightController

        remove_child verifies that the given row number is valid, and that the data
        at the given row == the given child.

        Parameters
        ----------
        child: Union[FlightLine, DataFile]
            The child primitive object to be removed
        row: int
            The row number of the child's controller wrapper
        confirm: bool Default[True]
            If True spawn a confirmation dialog requiring user input to confirm removal

        Returns
        -------
        bool:
            True on success
            False on fail e.g. child is not a member of this Flight, or not of appropriate type,
                or on a row/child mis-match

        """
        if confirm:
            if not helpers.confirm_action("Confirm Deletion",
                                          "Are you sure you want to delete %s" % str(child),
                                          self.controller.get_parent()):
                return False

        if not self._flight.remove_child(child):
            return False
        if isinstance(child, FlightLine):
            self._flight_lines.removeRow(row)
        elif isinstance(child, DataFile):
            self._data_files.removeRow(row)
        else:
            self.log.warning("Child of type: (%s) not removed from flight.", str(type(child)))
            return False
        return True

    # TODO: Can't test this
    def set_name(self, name: str = None, interactive=False):
        if interactive:
            name = helpers.get_input("Set Name", "Enter a new name:", self._flight.name)
        if name:
            self._flight.name = name
        self.update()

    def set_attr(self, key: str, value: Any):
        if key in Flight.__dict__ and isinstance(Flight.__dict__[key], property):
            setattr(self._flight, key, value)
            self.update()
        else:
            raise AttributeError("Attribute %s cannot be set for flight <%s>" % (key, str(self._flight)))

    def __hash__(self):
        return hash(self._flight.uid)

    def __str__(self):
        return str(self._flight)
