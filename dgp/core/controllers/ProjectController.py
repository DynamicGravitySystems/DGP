# -*- coding: utf-8 -*-
from typing import Optional, Union

from PyQt5.QtGui import QStandardItem

from core.controllers.FlightController import FlightController
from core.controllers.common import StandardProjectContainer
from core.models.flight import Flight, DataFile
from core.models.meter import Gravimeter
from core.oid import OID
from core.models.project import GravityProject, AirborneProject
from gui.dialogs import AdvancedImportDialog
from lib.enums import DataTypes


class ProjectController(QStandardItem):
    def __init__(self, project: GravityProject):
        super().__init__(project.name)
        self._project = project

    @property
    def project(self) -> GravityProject:
        return self._project

    def properties(self):
        print(self.__class__.__name__)


class AirborneProjectController(ProjectController):
    def __init__(self, project: AirborneProject):
        super().__init__(project)

        self.flights = StandardProjectContainer("Flights")
        self.appendRow(self.flights)

        self.meters = StandardProjectContainer("Gravimeters")
        self.appendRow(self.meters)

        self._controllers = {}

        for flight in self.project.flights:
            controller = FlightController(flight, controller=self)
            self._controllers[flight.uid] = controller
            self.flights.appendRow(controller)

        for meter in self.project.gravimeters:
            pass

    def properties(self):
        print(self.__class__.__name__)

    @property
    def project(self) -> Union[GravityProject, AirborneProject]:
        return super().project

    @property
    def flight_controllers(self):
        return [fc for fc in self._controllers.values() if isinstance(fc, FlightController)]

    @property
    def context_menu(self):
        return

    def add_flight(self, flight: Flight):
        self.project.add_child(flight)
        controller = FlightController(flight, controller=self)
        self._controllers[flight.uid] = controller
        self.flights.appendRow(controller)

    def add_child(self, child: Union[Flight, Gravimeter]):
        self.project.add_child(child)
        if isinstance(child, Flight):
            self.flights.appendRow(child)
        elif isinstance(child, Gravimeter):
            self.meters.appendRow(child)

    def remove_child(self, child: Union[Flight, Gravimeter], row: int):
        self.project.remove_child(child.uid)
        if isinstance(child, Flight):
            self.flights.removeRow(row)
        elif isinstance(child, Gravimeter):
            self.meters.removeRow(row)

        del self._controllers[child.uid]

    def get_controller(self, oid: OID):
        return self._controllers[oid]

    def load_data_file(self, _type: DataTypes, flight: Optional[Flight]=None, browse=True):
        dialog = AdvancedImportDialog(self.project, flight, _type.value)
        if browse:
            dialog.browse()

        if dialog.exec_():

            print("Loading file")
            controller = self._controllers[dialog.flight.uid]
            controller.add_child(DataFile('%s/%s/' % (flight.uid.base_uuid, _type.value.lower()), 'NoLabel',
                                              _type.value.lower(), dialog.path))

            # if _type == DataTypes.GRAVITY:
            #     loader = LoaderThread.from_gravity(self.parent(), dialog.path)
            # else:
            #     loader = LoaderThread.from_gps(None, dialog.path, 'hms')
            #
            # loader.result.connect(lambda: print("Finished importing stuff"))
            # loader.start()

    def getContextMenuBindings(self):
        return [
            ('addSeparator', ())
        ]

