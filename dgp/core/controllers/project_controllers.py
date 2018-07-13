# -*- coding: utf-8 -*-
import functools
import itertools
import logging
import shlex
import sys
from pathlib import Path
from pprint import pprint
from typing import Union, List

from PyQt5.QtCore import Qt, QProcess, QObject, QRegExp
from PyQt5.QtGui import QStandardItem, QBrush, QColor, QStandardItemModel, QIcon, QRegExpValidator
from PyQt5.QtWidgets import QWidget
from pandas import DataFrame

from dgp.core.file_loader import FileLoader
from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import (IAirborneController, IFlightController, IParent,
                                                        IDataSetController)
from dgp.core.hdf5_manager import HDF5Manager
from .flight_controller import FlightController
from .gravimeter_controller import GravimeterController
from .project_containers import ProjectFolder
from .controller_helpers import confirm_action, get_input
from dgp.core.controllers.controller_mixins import AttributeProxy
from dgp.gui.dialogs.add_flight_dialog import AddFlightDialog
from dgp.gui.dialogs.add_gravimeter_dialog import AddGravimeterDialog
from dgp.gui.dialogs.data_import_dialog import DataImportDialog
from dgp.gui.dialogs.project_properties_dialog import ProjectPropertiesDialog
from dgp.core.models.data import DataFile
from dgp.core.models.flight import Flight
from dgp.core.models.meter import Gravimeter
from dgp.core.models.project import GravityProject, AirborneProject
from dgp.core.types.enumerations import DataTypes
from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.trajectory_ingestor import import_trajectory

BASE_COLOR = QBrush(QColor('white'))
ACTIVE_COLOR = QBrush(QColor(108, 255, 63))
FLT_ICON = ":/icons/airborne"
MTR_ICON = ":/icons/meter_config.png"


class AirborneProjectController(IAirborneController, AttributeProxy):
    def __init__(self, project: AirborneProject):
        super().__init__(project.name)
        self.log = logging.getLogger(__name__)
        self._project = project
        self._parent = None
        self._active = None

        self.setIcon(QIcon(":/icons/dgs"))
        self.setToolTip(str(self._project.path.resolve()))
        self.setData(project, Qt.UserRole)

        self.flights = ProjectFolder("Flights", FLT_ICON)
        self.appendRow(self.flights)
        self.meters = ProjectFolder("Gravimeters", MTR_ICON)
        self.appendRow(self.meters)

        self._child_map = {Flight: self.flights,
                           Gravimeter: self.meters}

        for flight in self.project.flights:
            controller = FlightController(flight, parent=self)
            self.flights.appendRow(controller)

        for meter in self.project.gravimeters:
            controller = GravimeterController(meter, parent=self)
            self.meters.appendRow(controller)

        self._bindings = [
            ('addAction', ('Set Project Name', self.set_name)),
            ('addAction', ('Show in Explorer', self.show_in_explorer)),
            ('addAction', ('Project Properties', self.properties_dlg))
        ]

        # Experiment - declare underlying properties for UI use
        # dict key is the attr name (use get_attr to retrieve the value)
        # tuple of ( editable: True/False, Validator: QValidator )
        self._fields = {
            'name': (True, QRegExpValidator(QRegExp("[A-Za-z]+.{4,30}"))),
            'uid': (False, None),
            'path': (False, None),
            'description': (True, None),
            'create_date': (False, None),
            'modify_date': (False, None)
        }

    def validator(self, key: str):  # pragma: no cover
        if key in self._fields:
            return self._fields[key][1]
        return None

    def writeable(self, key: str):  # pragma: no cover
        if key in self._fields:
            return self._fields[key][0]
        return True

    @property
    def fields(self) -> List[str]:
        """Return list of public attribute keys (for UI display)"""
        return list(self._fields.keys())

    @property
    def uid(self) -> OID:
        return self._project.uid

    @property
    def datamodel(self) -> object:
        return self._project

    @property
    def project(self) -> Union[GravityProject, AirborneProject]:
        return self._project

    @property
    def path(self) -> Path:
        return self._project.path

    @property
    def menu_bindings(self):  # pragma: no cover
        return self._bindings

    @property
    def hdf5path(self) -> Path:
        return self._project.path.joinpath("dgpdata.hdf5")

    @property
    def meter_model(self) -> QStandardItemModel:
        return self.meters.internal_model

    @property
    def flight_model(self) -> QStandardItemModel:
        return self.flights.internal_model

    def get_parent_widget(self) -> Union[QObject, QWidget, None]:
        return self._parent

    def set_parent_widget(self, value: Union[QObject, QWidget]) -> None:
        self._parent = value

    def add_child(self, child: Union[Flight, Gravimeter]) -> Union[FlightController, GravimeterController, None]:
        if isinstance(child, Flight):
            controller = FlightController(child, parent=self)
            self.flights.appendRow(controller)
        elif isinstance(child, Gravimeter):
            controller = GravimeterController(child, parent=self)
            self.meters.appendRow(controller)
        else:
            raise ValueError("{0!r} is not a valid child type for {1.__name__}".format(child, self.__class__))
        self.project.add_child(child)
        self.update()
        return controller

    def remove_child(self, child: Union[Flight, Gravimeter], row: int, confirm=True):
        if not isinstance(child, (Flight, Gravimeter)):
            raise ValueError("{0!r} is not a valid child object".format(child))
        if confirm:  # pragma: no cover
            if not confirm_action("Confirm Deletion",
                                  "Are you sure you want to delete {!s}"
                                  .format(child.name)):
                return
        self.project.remove_child(child.uid)
        self._child_map[type(child)].removeRow(row)
        self.update()

    def get_child(self, uid: Union[str, OID]) -> Union[FlightController, GravimeterController, None]:
        for child in itertools.chain(self.flights.items(), self.meters.items()):
            if child.uid == uid:
                return child

    def get_active_child(self):
        return self._active

    def set_active_child(self, child: IFlightController, emit: bool = True):
        if isinstance(child, IFlightController):
            self._active = child
            for ctrl in self.flights.items():  # type: QStandardItem
                ctrl.setBackground(BASE_COLOR)
            child.setBackground(ACTIVE_COLOR)
            if emit and self.model() is not None:  # pragma: no cover
                self.model().flight_changed.emit(child)
        else:
            raise ValueError("Child of type {0!s} cannot be set to active.".format(type(child)))

    def save(self, to_file=True):
        return self.project.to_json(indent=2, to_file=to_file)

    def set_name(self):  # pragma: no cover
        new_name = get_input("Set Project Name", "Enter a Project Name", self.project.name)
        if new_name:
            self.set_attr('name', new_name)

    def show_in_explorer(self):  # pragma: no cover
        # TODO Linux KDE/Gnome file browser launch
        ppath = str(self.project.path.resolve())
        if sys.platform == 'darwin':
            script = 'oascript'
            args = '-e tell application \"Finder\" -e activate -e select POSIX file \"' + ppath + '\" -e end tell'
        elif sys.platform == 'win32':
            script = 'explorer'
            args = shlex.quote(ppath)
        else:
            self.log.warning("Platform %s is not supported for this action.", sys.platform)
            return

        QProcess.startDetached(script, shlex.split(args))

    # TODO: What to do about these dialog methods - it feels wrong here
    def add_flight(self):  # pragma: no cover
        dlg = AddFlightDialog(project=self, parent=self.get_parent_widget())
        return dlg.exec_()

    def add_gravimeter(self):  # pragma: no cover
        """Launch a Dialog to import a Gravimeter configuration"""
        dlg = AddGravimeterDialog(self, parent=self.get_parent_widget())
        return dlg.exec_()

    def update(self):  # pragma: no cover
        """Emit an update event from the parent Model, signalling that
        data has been added/removed/modified in the project."""
        self.setText(self._project.name)
        if self.model() is not None:
            self.model().project_changed.emit()

    def _post_load(self, datafile: DataFile, dataset: IDataSetController,
                   data: DataFrame) -> None:  # pragma: no cover
        """
        This is a slot called upon successful loading of a DataFile by a
        FileLoader Thread.

        Parameters
        ----------
        datafile : :obj:`dgp.core.models.data.DataFile`
            The DataFile reference object to be processed
        data : DataFrame
            The ingested pandas DataFrame to be dumped to the HDF5 store

        """
        # TODO: Insert DataFile into appropriate child
        datafile.set_parent(dataset)
        if HDF5Manager.save_data(data, datafile, path=self.hdf5path):
            self.log.info("Data imported and saved to HDF5 Store")
        dataset.add_datafile(datafile)
        return

    def load_file_dlg(self, datatype: DataTypes = DataTypes.GRAVITY,
                      flight: IFlightController = None,
                      dataset: IDataSetController = None) -> None:  # pragma: no cover
        """
        Project level dialog for importing/loading Gravity or Trajectory data
        files. The Dialog generates a DataFile and a parameter map (dict) which
        is passed along to a FileLoader thread to ingest the raw data-file.
        On completion of the FileLoader, AirborneProjectController._post_load is
        called, which saves the ingested data to the project's HDF5 file, and
        adds the DataFile object to the relevant parent.

        Parameters
        ----------
        datatype : DataTypes

        flight : IFlightController, optional
            Set the default flight selected when launching the dialog
        dataset : IDataSetController, optional
            Set the default Dataset selected when launching the dialog


        """
        def load_data(datafile: DataFile, params: dict, parent: IDataSetController):
            if datafile.group == 'gravity':
                method = read_at1a
            elif datafile.group == 'trajectory':
                method = import_trajectory
            else:
                self.log.error("Unrecognized data group: " + datafile.group)
                return
            loader = FileLoader(datafile.source_path, method,
                                parent=self.get_parent_widget(), **params)
            loader.loaded.connect(functools.partial(self._post_load, datafile,
                                                    parent))
            loader.start()

        dlg = DataImportDialog(self, datatype, parent=self.get_parent_widget())
        if flight is not None:
            dlg.set_initial_flight(flight)
        dlg.load.connect(load_data)
        dlg.exec_()

    def properties_dlg(self):  # pragma: no cover
        dlg = ProjectPropertiesDialog(self)
        dlg.exec_()
