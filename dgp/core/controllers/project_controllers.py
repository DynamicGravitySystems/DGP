# -*- coding: utf-8 -*-
import functools
import inspect
import logging
import shlex
import sys
from pathlib import Path
from weakref import WeakSet
from typing import Optional, Union, Generator, Callable, Any

from PyQt5.QtCore import Qt, QProcess, QThread, pyqtSignal, QObject, pyqtSlot
from PyQt5.QtGui import QStandardItem, QBrush, QColor, QStandardItemModel, QIcon
from PyQt5.QtWidgets import QWidget
from pandas import DataFrame

from dgp.core.controllers.controller_interfaces import IAirborneController
from . import project_containers
from .hdf5_controller import HDFController
from .flight_controller import FlightController
from .gravimeter_controller import GravimeterController
from .project_containers import ProjectFolder
from .controller_helpers import confirm_action
from dgp.core.controllers.controller_mixins import PropertiesProxy
from dgp.gui.dialog.add_flight_dialog import AddFlightDialog
from dgp.gui.dialog.add_gravimeter_dialog import AddGravimeterDialog
from dgp.gui.dialog.data_import_dialog import DataImportDialog
from dgp.core.models.data import DataFile
from dgp.core.models.flight import Flight
from dgp.core.models.meter import Gravimeter
from dgp.core.models.project import GravityProject, AirborneProject
from dgp.core.types.enumerations import DataTypes
from dgp.lib.etc import align_frames
from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.trajectory_ingestor import import_trajectory

BASE_COLOR = QBrush(QColor('white'))
ACTIVE_COLOR = QBrush(QColor(108, 255, 63))
FLT_ICON = ":/icons/airborne"
MTR_ICON = ":/icons/meter_config.png"


class FileLoader(QThread):
    completed = pyqtSignal(DataFrame, Path)
    error = pyqtSignal(str)

    def __init__(self, path: Path, method: Callable, parent, **kwargs):
        super().__init__(parent=parent)
        self._path = Path(path)
        self._method = method
        self._kwargs = kwargs

    def run(self):
        try:
            sig = inspect.signature(self._method)
            kwargs = {k: v for k, v in self._kwargs.items() if k in sig.parameters}
            result = self._method(str(self._path), **kwargs)
        except Exception as e:
            self.error.emit(str(e))
        else:
            self.completed.emit(result, self._path)


class AirborneProjectController(IAirborneController, PropertiesProxy):
    def __init__(self, project: AirborneProject, parent: QObject = None):
        super().__init__(project.name)
        self.log = logging.getLogger(__name__)
        self._parent = parent
        self._project = project
        self._hdfc = HDFController(self._project.path)
        self._active = None

        self.setIcon(QIcon(":/icons/dgs"))
        self.setToolTip(str(self._project.path.resolve()))
        self.setData(project, Qt.UserRole)

        self.flights = ProjectFolder("Flights", FLT_ICON)
        self.appendRow(self.flights)
        self.meters = ProjectFolder("Gravimeters", MTR_ICON)
        self.appendRow(self.meters)

        self.flight_controls = WeakSet()
        self.meter_controls = WeakSet()

        for flight in self.project.flights:
            controller = FlightController(flight, controller=self)
            self.flight_controls.add(controller)
            self.flights.appendRow(controller)

        for meter in self.project.gravimeters:
            controller = GravimeterController(meter, controller=self)
            self.meter_controls.add(controller)
            self.meters.appendRow(controller)

        self._bindings = [
            ('addAction', ('Set Project Name', self.set_name)),
            ('addAction', ('Show in Explorer', self.show_in_explorer))
        ]

    @property
    def proxied(self) -> object:
        return self._project

    def properties(self):
        print(self.__class__.__name__)

    def get_parent(self) -> Union[QObject, QWidget, None]:
        return self._parent

    def set_parent(self, value: Union[QObject, QWidget]) -> None:
        self._parent = value

    @property
    def menu_bindings(self):
        return self._bindings

    @property
    def hdf5store(self) -> HDFController:
        return self._hdfc

    @property
    def flight_ctrls(self) -> Generator[FlightController, None, None]:
        for ctrl in self.flight_controls:
            yield ctrl

    @property
    def project(self) -> Union[GravityProject, AirborneProject]:
        return self._project

    @property
    def meter_model(self) -> QStandardItemModel:
        return self.meters.internal_model

    @property
    def flight_model(self) -> QStandardItemModel:
        return self.flights.internal_model

    def add_child(self, child: Union[Flight, Gravimeter]):
        self.project.add_child(child)
        self.update()
        if isinstance(child, Flight):
            controller = FlightController(child, controller=self)
            self.flight_controls.add(controller)
            self.flights.appendRow(controller)
        elif isinstance(child, Gravimeter):
            controller = GravimeterController(child, controller=self)
            self.meter_controls.add(controller)
            self.meters.appendRow(controller)
        else:
            print("Invalid child: " + str(type(child)))
            return
        return controller

    def remove_child(self, child: Union[Flight, Gravimeter], row: int, confirm=True):
        if confirm:
            if not confirm_action("Confirm Deletion", "Are you sure you want to delete %s"
                                                      % child.name):
                return
        self.project.remove_child(child.uid)
        self.update()
        if isinstance(child, Flight):
            self.flights.removeRow(row)
        elif isinstance(child, Gravimeter):
            self.meters.removeRow(row)

    def get_child_controller(self, child: Union[Flight, Gravimeter]):
        ctrl_map = {Flight: self.flight_ctrls, Gravimeter: self.meter_controls}
        ctrls = ctrl_map.get(type(child), None)
        if ctrls is None:
            return None

        for ctrl in ctrls:
            if ctrl.uid == child.uid:
                return ctrl

    def get_active_child(self):
        return self._active

    def set_active_child(self, child: FlightController, emit: bool = True):
        if isinstance(child, FlightController):
            self._active = child
            for ctrl in self.flight_controls:  # type: QStandardItem
                ctrl.setBackground(BASE_COLOR)
            child.setBackground(ACTIVE_COLOR)
            if emit:
                self.model().flight_changed.emit(child)

    def set_name(self):
        new_name = project_containers.get_input("Set Project Name", "Enter a Project Name", self.project.name)
        if new_name:
            self.project.name = new_name
            self.setData(new_name, Qt.DisplayRole)

    def show_in_explorer(self):
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

    def add_flight(self):
        dlg = AddFlightDialog(project=self, parent=self.get_parent())
        return dlg.exec_()

    def add_gravimeter(self):
        """Launch a Dialog to import a Gravimeter configuration"""
        dlg = AddGravimeterDialog(self, parent=self.get_parent())
        return dlg.exec_()

    def update(self):
        """Emit an update event from the parent Model, signalling that
        data has been added/removed/modified in the project."""
        self.model().project_changed.emit()

    def _post_load(self, datafile: DataFile, data: DataFrame):



        # try:
        #     fltid, grpid, uid, path = self.hdf5store.save_data(data, flight.uid.base_uuid, 'gravity')
        # except IOError:
        #     self.log.exception("Error writing data to HDF5 file.")
        # else:
        #     datafile = DataFile(hdfpath=path, label='', group=grpid, source_path=src_path, uid=uid)
        #     flight.add_child(datafile)

        print(data.describe())
        print("Post_load loading datafile: " + str(datafile))
        if self.hdf5store.save_data(data, datafile):
            print("Data saved to HDFStore")

        return

        # TODO: Implement align_frames functionality as below

        # gravity = flight.gravity
        # trajectory = flight.trajectory
        # if gravity is not None and trajectory is not None:
        #     # align and crop the gravity and trajectory frames
        #
        #     from lib.gravity_ingestor import DGS_AT1A_INTERP_FIELDS
        #     from lib.trajectory_ingestor import TRAJECTORY_INTERP_FIELDS
        #
        #     fields = DGS_AT1A_INTERP_FIELDS | TRAJECTORY_INTERP_FIELDS
        #     new_gravity, new_trajectory = align_frames(gravity, trajectory,
        #                                                interp_only=fields)
        #
        #     # TODO: Fix this mess
        #     # replace datasource objects
        #     ds_attr = {'path': gravity.filename, 'dtype': gravity.dtype}
        #     flight.remove_data(gravity)
        #     self._add_data(new_gravity, ds_attr['dtype'], flight,
        #                    ds_attr['path'])
        #
        #     ds_attr = {'path': trajectory.filename,
        #                'dtype': trajectory.dtype}
        #     flight.remove_data(trajectory)
        #     self._add_data(new_trajectory, ds_attr['dtype'], flight,
        #                    ds_attr['path'])

    def load_file(self, datatype: DataTypes = DataTypes.GRAVITY):
        def load_data(datafile: DataFile):
            if datafile.group == 'gravity':
                method = read_at1a
            elif datafile.group == 'trajectory':
                method = import_trajectory
            else:
                return
            loader = FileLoader(datafile.source_path, method, parent=self.get_parent())
            loader.completed.connect(functools.partial(self._post_load, datafile))
            loader.start()

        dlg = DataImportDialog(self, datatype, parent=self.get_parent())
        dlg.load.connect(load_data)
        dlg.exec_()

    # Deprecated - dialog will handle
    def _load_file(self, ftype: DataTypes, destination: Optional[FlightController] = None, browse=True):
        pass
        # dialog = DataImportDialog(self, ftype, self.get_parent())
        # dialog.set_initial_flight(self.active_entity)
        # if browse:
        #     dialog.browse()
        #
        # if dialog.exec_():
        #     flt_uid = dialog.flight  # type: OID
        #     fc = self.get_child_controller(flt_uid.reference)
        #     if fc is None:
        #         # Error
        #         return
        #
        #     if ftype == DataTypes.GRAVITY:
        #         method = read_at1a
        #     elif ftype == DataTypes.TRAJECTORY:
        #         method = import_trajectory
        #     else:
        #         print("Unknown datatype %s" % str(ftype))
        #         return
        #     # Note loader must be passed a QObject parent or it will crash
        #     loader = FileLoader(dialog.path, method, parent=self._parent, **dialog.params)
        #     loader.completed.connect(functools.partial(self._post_load, fc))
        #
        #     loader.start()

            # self.update()

        # Old code from Main: (for reference)

        # prog = self.show_progress_status(0, 0)
        # prog.setValue(1)

        # def _on_err(result):
        #     err, exc = result
        #     prog.close()
        #     if err:
        #         msg = "Error loading {typ}::{fname}".format(
        #             typ=dtype.name.capitalize(), fname=params.get('path', ''))
        #         self.log.error(msg)
        #     else:
        #         msg = "Loaded {typ}::{fname}".format(
        #             typ=dtype.name.capitalize(), fname=params.get('path', ''))
        #         self.log.info(msg)
        #
        # ld = loader.get_loader(parent=self, dtype=dtype, on_complete=self._post_load,
        #                        on_error=_on_err, **params)
        # ld.start()

    def save(self):
        print("Saving project")
        return self.project.to_json(indent=2, to_file=True)


class MarineProjectController:
    def load_file(self, ftype, destination: Optional[Any] = None) -> None:
        pass

    def set_active(self, entity, **kwargs):
        pass

    def add_child(self, child):
        pass

    def remove_child(self, child, row: int, confirm: bool = True):
        pass
