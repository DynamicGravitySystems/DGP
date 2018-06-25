# -*- coding: utf-8 -*-
import logging
import shlex
import sys
from weakref import WeakSet
from typing import Optional, Union, Generator

from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QStandardItem, QBrush, QColor

from core.controllers import common
from core.controllers.FlightController import FlightController
from core.controllers.MeterController import GravimeterController
from core.controllers.common import StandardProjectContainer, BaseProjectController, confirm_action
from core.models.flight import Flight, DataFile
from core.models.meter import Gravimeter
from core.models.project import GravityProject, AirborneProject
from core.oid import OID
from gui.dialogs import AdvancedImportDialog
from lib.enums import DataTypes

BASE_COLOR = QBrush(QColor('white'))
ACTIVE_COLOR = QBrush(QColor(108, 255, 63))


class AirborneProjectController(BaseProjectController):
    def __init__(self, project: AirborneProject):
        super().__init__(project)
        self.log = logging.getLogger(__name__)

        self.flights = StandardProjectContainer("Flights")
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

    def add_child(self, child: Union[Flight, Gravimeter]):
        self.project.add_child(child)
        if isinstance(child, Flight):
            controller = FlightController(child, controller=self)
            self._flight_ctrl.add(controller)
            self.flights.appendRow(controller)
        elif isinstance(child, Gravimeter):
            controller = GravimeterController(child, controller=self)
            self._meter_ctrl.add(controller)
            self.meters.appendRow(controller)

    def get_child_controller(self, child: Union[Flight, Gravimeter]):
        ctrl_map = {Flight: self.flight_ctrls, Gravimeter: self.meter_ctrls}
        ctrls = ctrl_map.get(type(child), None)
        if ctrls is None:
            return None

        for ctrl in ctrls:
            if ctrl.entity.uid == child.uid:
                return ctrl

    def remove_child(self, child: Union[Flight, Gravimeter], row: int, confirm=True):
        if confirm:
            if not confirm_action("Confirm Deletion", "Are you sure you want to delete %s"
                                                      % child.name):
                return

        self.project.remove_child(child.uid)
        if isinstance(child, Flight):
            self.flights.removeRow(row)
        elif isinstance(child, Gravimeter):
            self.meters.removeRow(row)

    def set_active(self, entity: FlightController):
        if isinstance(entity, FlightController):
            self._active = entity

            for ctrl in self._flight_ctrl:  # type: QStandardItem
                ctrl.setBackground(BASE_COLOR)
            entity.setBackground(ACTIVE_COLOR)
            self.model().flight_changed.emit(entity)

    def set_name(self):
        new_name = common.get_input("Set Project Name", "Enter a Project Name", self.project.name)
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

    def load_data_file(self, _type: DataTypes, flight: Optional[Flight] = None, browse=True):
        dialog = AdvancedImportDialog(self.project, flight, _type.value)
        if browse:
            dialog.browse()

        if dialog.exec_():

            print("Loading file")
            controller = self.get_child_controller(dialog.flight)
            print("Got controller: " + str(controller))
            print("Controller flight: " + controller.entity.name)
            # controller = self.flight_ctrls[dialog.flight.uid]
            # controller.add_child(DataFile('%s/%s/' % (flight.uid.base_uuid, _type.value.lower()), 'NoLabel',
            #                               _type.value.lower(), dialog.path))

            # TODO: Actually load the file (should we use a worker queue for loading?)

    @property
    def menu_bindings(self):
        return self._bindings


class MarineProjectController(BaseProjectController):
    def set_active(self, entity):
        pass

    def add_child(self, child):
        pass

    def remove_child(self, child, row: int, confirm: bool = True):
        pass
