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
from pandas import DataFrame

from core.controllers import Containers
from core.controllers.FlightController import FlightController
from core.controllers.MeterController import GravimeterController
from core.controllers.Containers import StandardProjectContainer, confirm_action
from core.controllers.BaseProjectController import BaseProjectController
from core.models.data import DataFile
from core.models.flight import Flight
from core.models.meter import Gravimeter
from core.models.project import GravityProject, AirborneProject
from core.oid import OID
from core.types.enumerations import DataTypes
from gui.dialogs import AdvancedImportDialog
from lib.etc import align_frames
from lib.gravity_ingestor import read_at1a
from lib.trajectory_ingestor import import_trajectory

BASE_COLOR = QBrush(QColor('white'))
ACTIVE_COLOR = QBrush(QColor(108, 255, 63))
FLT_ICON = ":/icons/airborne"


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
            self.error.emit(e)
        else:
            self.completed.emit(result, self._path)


class AirborneProjectController(BaseProjectController):
    def __init__(self, project: AirborneProject, parent: QObject = None):
        super().__init__(project)
        self._parent = parent
        self.setIcon(QIcon(":/icons/dgs"))
        self.log = logging.getLogger(__name__)

        self.flights = StandardProjectContainer("Flights", FLT_ICON)
        self.appendRow(self.flights)

        self.meters = StandardProjectContainer("Gravimeters")
        self.appendRow(self.meters)

        self._flight_ctrl = WeakSet()
        self._meter_ctrl = WeakSet()
        self._active = None

        for flight in self.project.flights:
            controller = FlightController(flight, controller=self)
            self._flight_ctrl.add(controller)
            self.flights.appendRow(controller)

        for meter in self.project.gravimeters:
            controller = GravimeterController(meter, controller=self)
            self._meter_ctrl.add(controller)
            self.meters.appendRow(controller)

        self._bindings = [
            ('addAction', ('Set Project Name', self.set_name)),
            ('addAction', ('Show in Explorer', self.show_in_explorer))
        ]

    def properties(self):
        print(self.__class__.__name__)

    @property
    def menu_bindings(self):
        return self._bindings

    @property
    def flight_ctrls(self) -> Generator[FlightController, None, None]:
        for ctrl in self._flight_ctrl:
            yield ctrl

    @property
    def meter_ctrls(self) -> Generator[GravimeterController, None, None]:
        for ctrl in self._meter_ctrl:
            yield ctrl

    @property
    def project(self) -> Union[GravityProject, AirborneProject]:
        return super().project

    @property
    def flight_model(self) -> QStandardItemModel:
        return self.flights.internal_model

    @property
    def meter_model(self) -> QStandardItemModel:
        return self.meters.internal_model

    def add_child(self, child: Union[Flight, Gravimeter]):
        self.project.add_child(child)
        self.update()
        if isinstance(child, Flight):
            controller = FlightController(child, controller=self)
            self._flight_ctrl.add(controller)
            self.flights.appendRow(controller)
        elif isinstance(child, Gravimeter):
            controller = GravimeterController(child, controller=self)
            self._meter_ctrl.add(controller)
            self.meters.appendRow(controller)
        else:
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
        ctrl_map = {Flight: self.flight_ctrls, Gravimeter: self.meter_ctrls}
        ctrls = ctrl_map.get(type(child), None)
        if ctrls is None:
            return None

        for ctrl in ctrls:
            if ctrl.entity.uid == child.uid:
                return ctrl

    def set_active(self, controller: FlightController, emit: bool = True):
        if isinstance(controller, FlightController):
            self._active = controller

            for ctrl in self._flight_ctrl:  # type: QStandardItem
                ctrl.setBackground(BASE_COLOR)
            controller.setBackground(ACTIVE_COLOR)
            if emit:
                self.model().flight_changed.emit(controller)

    def set_name(self):
        new_name = Containers.get_input("Set Project Name", "Enter a Project Name", self.project.name)
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

    def update(self):
        """Emit an update event from the parent Model, signalling that
        data has been added/removed/modified in the project."""
        self.model().project_changed.emit()

    @pyqtSlot(DataFrame, Path, name='_post_load')
    def _post_load(self, flight: FlightController, data: DataFrame, src_path: Path):
        try:
            fltid, grpid, uid, path = self.hdf5store.save_data(data, flight.uid.base_uuid, 'gravity')
        except IOError:
            self.log.exception("Error writing data to HDF5 file.")
        else:
            datafile = DataFile(hdfpath=path, label='', group=grpid, source_path=src_path, uid=uid)
            flight.add_child(datafile)

        return

        # TODO: Implement align_frames functionality as below

        gravity = flight.gravity
        trajectory = flight.trajectory
        if gravity is not None and trajectory is not None:
            # align and crop the gravity and trajectory frames

            from lib.gravity_ingestor import DGS_AT1A_INTERP_FIELDS
            from lib.trajectory_ingestor import TRAJECTORY_INTERP_FIELDS

            fields = DGS_AT1A_INTERP_FIELDS | TRAJECTORY_INTERP_FIELDS
            new_gravity, new_trajectory = align_frames(gravity, trajectory,
                                                       interp_only=fields)

            # TODO: Fix this mess
            # replace datasource objects
            ds_attr = {'path': gravity.filename, 'dtype': gravity.dtype}
            flight.remove_data(gravity)
            self._add_data(new_gravity, ds_attr['dtype'], flight,
                           ds_attr['path'])

            ds_attr = {'path': trajectory.filename,
                       'dtype': trajectory.dtype}
            flight.remove_data(trajectory)
            self._add_data(new_trajectory, ds_attr['dtype'], flight,
                           ds_attr['path'])

    def load_file(self, ftype: DataTypes, destination: Optional[FlightController] = None, browse=True):
        dialog = AdvancedImportDialog(self, destination, ftype.value)
        if browse:
            dialog.browse()

        if dialog.exec_():
            flt_uid = dialog.flight  # type: OID
            fc = self.get_child_controller(flt_uid.reference)
            if fc is None:
                # Error
                return

            if ftype == DataTypes.GRAVITY:
                method = read_at1a
            elif ftype == DataTypes.TRAJECTORY:
                method = import_trajectory
            else:
                print("Unknown datatype %s" % str(ftype))
                return
            # Note loader must be passed a QObject parent or it will crash
            loader = FileLoader(dialog.path, method, parent=self._parent, **dialog.params)
            loader.completed.connect(functools.partial(self._post_load, fc))

            loader.start()

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


class MarineProjectController(BaseProjectController):
    def load_file(self, ftype, destination: Optional[Any] = None) -> None:
        pass

    def set_active(self, entity, **kwargs):
        pass

    def add_child(self, child):
        pass

    def remove_child(self, child, row: int, confirm: bool = True):
        pass
