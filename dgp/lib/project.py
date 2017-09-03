# coding: utf-8

import os
import uuid
import pickle

from pandas import HDFStore
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtCore import QObject, pyqtSignal

from .meterconfig import MeterConfig, AT1Meter
from dgp.lib.types import location, stillreading, flightline, DataPacket

"""
Dynamic Gravity Processor (DGP) :: project.py
License: Apache License V2

Overview:
project.py provides the object framework for setting up a gravity processing project, which may include project specific
configurations and settings, project specific files and imports, and the ability to segment a project into individual
flights and flight lines.

Workflow:
    User creates new project - enters project name, description, and location to save project.
        - User can additionaly define survey parameters specific to the project
        - User can then add a Gravity Meter configuration to the project
        - User then creates new flights each day a flight is flown, flight parameters are defined
        - Data files are imported into project and associated with a flight
            - Upon import the file will be converted to pandas DataFrame then written out to the
            project directory as HDF5.

        - User selects between flights in GUI to view in plot, data is pulled from the Flight object

"""


class GravityProject:
    """
    GravityProject will be the base class defining common values for both airborne
    and marine gravity survey projects.
    """
    def __init__(self, path, name: str="Untitled Project", description: str=None):
        """
        :param path: Project directory path - where all project files will be stored
        :param name: Project name
        :param description: Project description
        """
        super().__init__()
        if os.path.exists(path):
            self.projectdir = path
        else:
            raise FileNotFoundError
        if not os.path.isdir(self.projectdir):
            self.projectdir, _ = os.path.split(self.projectdir)

        self.name = name
        self.description = description

        self.hdf_path = os.path.join(self.projectdir, 'prjdata.h5')

        # Store MeterConfig objects in dictionary keyed by the meter name
        self.sensors = {}

        # TODO: Should data_sources point to the original imported files, or more likely to the project directory?
        self.data_sources = {}

    def add_meter(self, meter: MeterConfig) -> MeterConfig:
        """Add an existing MeterConfig class to the dictionary of available meters"""
        if isinstance(meter, MeterConfig):
            self.sensors[meter.name] = meter
            return self.sensors[meter.name]
        else:
            raise ValueError("meter parameter is not an instance of MeterConfig")

    def import_meter(self, path):
        """Import a meter configuration from an ini file and add it to the sensors dict"""
        # TODO: Way to construct different meter types (other than AT1 meter) dynamically
        if os.path.exists(path):
            try:
                meter = AT1Meter.from_ini(path)
                self.sensors[meter.name] = meter
            except ValueError:
                raise ValueError("Meter .ini file could not be imported, check format.")
            else:
                return self.sensors[meter.name]
        else:
            raise OSError("Path {} doesn't exist.".format(path))

    @property
    def meters(self):
        """Return list of meter names assigned to this project."""
        if not self.sensors:
            return []
        else:
            return list(self.sensors.keys())

    def save(self, path=None):
        """
        Export the project class as a pickled python object
        :param path: Path to save file
        :return:
        """
        if path is None:
            path = os.path.join(self.projectdir, '{}.d2p'.format(self.name))
        with open(path, 'wb') as f:
            pickle.dump(self, f)
        return True

    @staticmethod
    def load(path):
        """Use python pickling to load project"""
        with open(path, 'rb') as pickled:
            project = pickle.load(pickled)
            # Override whatever the project dir was with the directory where it was opened
            project.projectdir = os.path.normpath(os.path.dirname(path))
        return project


class Flight:
    """
    Define a Flight class used to record and associate data with an entire survey flight (takeoff -> landing)
    This class is iterable, yielding the flightlines named tuple objects from its lines dictionary
    """
    def __init__(self, meter: MeterConfig, **kwargs):
        # If uuid is passed use the value else assign new uuid
        # the letter 'f' is prepended to the uuid to ensure that we have a natural python name
        # as python variables cannot start with a number (this takes care of warning when storing data in pytables)
        self.uid = kwargs.get('uuid', 'f{}'.format(uuid.uuid4().hex))
        self.meter = meter

        # Known Absolute Site Reading/Location
        self.tie_value = None
        self.tie_location = None

        self.pre_still_reading = None
        self.post_still_reading = None

        self.flight_timeshift = 0

        # Flight data files
        self.data = {}

        # Flight lines keyed by UUID
        self.lines = {}

    def set_gravity_tie(self, gravity: float, loc: location):
        self.tie_value = gravity
        self.tie_location = loc

    def pre_still_reading(self, gravity: float, loc: location, time: float):
        self.pre_still_reading = stillreading(gravity, loc, time)

    def post_still_reading(self, gravity: float, loc: location, time: float):
        self.post_still_reading = stillreading(gravity, loc, time)

    def add_line(self, start: float, end: float):
        """Add a flight line to the flight by start/stop index and sequence number"""
        uid = uuid.uuid4().hex
        line = flightline(uid, len(self.lines), None, start, end)
        self.lines[uid] = line
        return line

    def __iter__(self):
        """Iterate over flight lines in the Flight instance"""
        for k, line in self.lines.items():
            yield line

    def __len__(self):
        return len(self.lines)


class AirborneProject(GravityProject):
    """
    A subclass of the base GravityProject, AirborneProject will define an Airborne survey
    project with parameters unique to airborne operations, and defining flight lines etc.

    This class is iterable, yielding the Flight objects contained within its flights dictionary
    """
    def __init__(self, path, name, description=None):
        super().__init__(path, name, description)

        # Dictionary of Flight objects keyed by the flight uuid
        self.flights = {}

    def get_data(self, flight: Flight):
        with HDFStore(self.hdf_path) as store:
            try:
                gravity = store.get('gravity/{}'.format(flight.uid))
            except KeyError:
                gravity = None
            try:
                gps = store.get('gps/{}'.format(flight.uid))
            except KeyError:
                gps = None
        return gravity, gps

    def add_data(self, packet: DataPacket):
        """
        Import a data file into the project
        :param packet: DataPacket custom class containing file path, dataframe, data type and flight association
        :return: Void
        """
        print("Ingesting data and exporting to hdf5 store")
        self.data_sources[uuid.uuid4().hex] = (packet.path, packet.flight.uid)

        assoc_flight = self.flights.get(packet.flight.uid, None)

        with HDFStore(self.hdf_path) as store:
            store.put('gravity/{}'.format(assoc_flight.uid), packet.data, format='table', data_columns=True)
        self.save()
        del packet

    def add_flight(self, flight: Flight):
        self.flights[flight.uid] = flight

    def get_flight(self, flight_id):
        flt = self.flights.get(flight_id, None)
        print("<Project> flight found: {}".format(flt))
        return flt

    def generate_model(self):
        """Generate a Qt Model based on the project structure."""
        model = QStandardItemModel()
        root = model.invisibleRootItem()

        # TODO: Add these icon resources to library or something so they are not loaded every time
        dgs_ico = QIcon('ui/assets/DGSIcon.xpm')
        flt_ico = QIcon('ui/assets/flight_icon.png')

        prj_header = QStandardItem(dgs_ico, "{name}: {path}".format(name=self.name, path=self.projectdir))
        prj_header.setEditable(False)
        fli_header = QStandardItem(flt_ico, "Flights")
        fli_header.setEditable(False)
        # TODO: Add a human readable identifier to flights
        for uid, flight in self.flights.items():
            fli_item = QStandardItem(flt_ico, "Flight: {}".format(uid))
            fli_item.setEditable(False)

            flight_data = [fpath for fpath, fuid in self.data_sources.values() if fuid == uid]
            for file in flight_data:
                file_item = QStandardItem("File {}".format(file))
                file_item.setEditable(False)
                fli_item.appendRow(file_item)

            for line in flight:
                line_item = QStandardItem("Line {}:{}".format(line.start, line.end))
                line_item.setEditable(False)
                fli_item.appendRow(line_item)
            fli_header.appendRow(fli_item)
        prj_header.appendRow(fli_header)

        root.appendRow(prj_header)
        return model

    def __iter__(self):
        for uid, flight in self.flights.items():
            yield flight

    def __len__(self):
        return len(self.flights)

    def __str__(self):
        return "Project: {name}\nPath: {path}\nDescription: {desc}".format(name=self.name,
                                                                           path=self.projectdir,
                                                                           desc=self.description)
