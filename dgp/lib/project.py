# coding: utf-8

import uuid
import pickle
import pathlib
import logging

from pandas import HDFStore
from PyQt5 import QtCore
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon


from .meterconfig import MeterConfig, AT1Meter
from dgp.lib.types import Location, StillReading, FlightLine, DataPacket

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


def can_pickle(attribute):
    """Helper function used by __getstate__ to determine if an attribute should be pickled."""
    # TODO: As necessary change this to check against a list of un-pickleable types
    if isinstance(attribute, logging.Logger):
        return False
    return True


class GravityProject:
    """
    GravityProject will be the base class defining common values for both airborne
    and marine gravity survey projects.
    """
    def __init__(self, path: pathlib.Path, name: str="Untitled Project", description: str=None):
        """
        :param path: Project directory path - where all project files will be stored
        :param name: Project name
        :param description: Project description
        """
        self.log = logging.getLogger(__name__)
        if isinstance(path, pathlib.Path):
            self.projectdir = path  # type: pathlib.Path
        else:
            self.projectdir = pathlib.Path(path)

        if not self.projectdir.is_dir():
            raise FileNotFoundError

        self.name = name
        self.description = description

        # self.hdf_path = os.path.join(self.projectdir, 'prjdata.h5')
        self.hdf_path = self.projectdir.joinpath('prjdata.h5')

        # Store MeterConfig objects in dictionary keyed by the meter name
        self.sensors = {}

        self.log.debug("Gravity Project Initialized")

    def add_meter(self, meter: MeterConfig) -> MeterConfig:
        """Add an existing MeterConfig class to the dictionary of available meters"""
        if isinstance(meter, MeterConfig):
            self.sensors[meter.name] = meter
            return self.sensors[meter.name]
        else:
            raise ValueError("meter parameter is not an instance of MeterConfig")

    def import_meter(self, path: pathlib.Path):
        """Import a meter configuration from an ini file and add it to the sensors dict"""
        # TODO: Way to construct different meter types (other than AT1 meter) dynamically
        if path.exists():
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

    def save(self, path: pathlib.Path=None):
        """
        Export the project class as a pickled python object
        :param path: Path to save file
        :return:
        """
        if path is None:
            path = self.projectdir.joinpath('{}.d2p'.format(self.name))
        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)
        with path.open('wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path):
        """Use python pickling to load project"""
        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)
        if not path.exists():
            raise FileNotFoundError

        with path.open('rb') as pickled:
            project = pickle.load(pickled)
            # Override whatever the project dir was with the directory where it was opened
            project.projectdir = path.parent
        return project

    def __getstate__(self):
        """Prune any non-pickleable objects from the class __dict__"""
        return {k: v for k, v in self.__dict__.items() if can_pickle(v)}

    def __setstate__(self, state):
        """Re-initialize a logger upon un-pickling"""
        self.__dict__ = state
        self.log = logging.getLogger(__name__)


class Flight:
    """
    Define a Flight class used to record and associate data with an entire survey flight (takeoff -> landing)
    This class is iterable, yielding the flightlines named tuple objects from its lines dictionary
    """
    def __init__(self, parent, name: str, meter: MeterConfig=None, **kwargs):
        """
        The Flight object represents a single literal survey flight, and accepts various parameters related to the
        flight.
        Currently a single GPS data and Gravity data file each may be assigned to a flight. In the future this
        functionality must be expanded to handle more complex cases requiring the input of multiple data files.
        At present a single gravity meter may be assigned to the flight. In future, as/if the project requires this
        may be expanded to allow for a second meter to be optionally assigned.
        :param parent: GravityProject - the Parent project item of this meter, used to retrieve linked data.
        :param name: Str - a human readable reference name for the flight
        :param meter: MeterConfig - a Gravity meter configuration object that will be associated with this flight.
        :param kwargs: Optional key-word arguments may be passed to assign other attributes, e.g. date within the flight
                date: a Datetime object specifying the date of the flight
                uuid: a UUID string to assign to this flight (otherwise a random UUID is generated upon creation)
        """
        # If uuid is passed use the value else assign new uuid
        # the letter 'f' is prepended to the uuid to ensure that we have a natural python name
        # as python variables cannot start with a number (this takes care of warning when storing data in pytables)
        self.parent = parent
        self.name = name
        self.uid = kwargs.get('uuid', 'f{}'.format(uuid.uuid4().hex))
        self.meter = meter
        if 'date' in kwargs:
            self.date = kwargs['date']

        self.log = logging.getLogger(__name__)

        # These private attributes will hold a file reference string used to retrieve data from hdf5 store.
        self._gpsdata = None  # type: str
        self._gravdata = None  # type: str

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

    @property
    def gps(self):
        return self.parent.load_data(self._gpsdata, 'gps')

    @gps.setter
    def gps(self, value):
        if self._gpsdata:
            self.log.warning('GPS Data File already exists, overwriting with new value.')
        self._gpsdata = value

    @property
    def gps_file(self):
        try:
            return self.parent.data_map[self._gpsdata], self._gpsdata
        except KeyError:
            return None, None

    @property
    def gravity(self):
        self.log.warning("Loading gravity data from file. (Expensive Operation)")
        return self.parent.load_data(self._gravdata, 'gravity')

    @gravity.setter
    def gravity(self, value):
        if self._gravdata:
            self.log.warning('Gravity Data File already exists, overwriting with new value.')
        self._gravdata = value

    @property
    def gravity_file(self):
        try:
            return self.parent.data_map[self._gravdata], self._gravdata
        except KeyError:
            return None, None

    def get_channel_data(self, channel):
        return self.gravity[channel]

    def set_gravity_tie(self, gravity: float, loc: Location):
        self.tie_value = gravity
        self.tie_location = loc

    def pre_still_reading(self, gravity: float, loc: Location, time: float):
        self.pre_still_reading = StillReading(gravity, loc, time)

    def post_still_reading(self, gravity: float, loc: Location, time: float):
        self.post_still_reading = StillReading(gravity, loc, time)

    def add_line(self, start: float, end: float):
        """Add a flight line to the flight by start/stop index and sequence number"""
        uid = uuid.uuid4().hex
        line = FlightLine(uid, len(self.lines), None, start, end)
        self.lines[uid] = line
        return line

    def __iter__(self):
        """Iterate over flight lines in the Flight instance"""
        for k, line in self.lines.items():
            yield line

    def __len__(self):
        return len(self.lines)

    def __str__(self):
        return "Flight: {name} UID:{uid}\nMeter:{meter}\nNum Lines:{lines}".format(
            name=self.name, uid=self.uid, meter=self.meter.name, lines=len(self))

    def __getstate__(self):
        return {k: v for k, v in self.__dict__.items() if can_pickle(v)}

    def __setstate__(self, state):
        self.__dict__ = state
        self.log = logging.getLogger(__name__)


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
        self.active = None  # type: Flight
        self.log.debug("Airborne project initialized")
        self.data_map = {}

    def set_active(self, flight_id):
        flight = self.get_flight(flight_id)
        self.active = flight

    def load_data(self, uid: str, prefix: str):
        """
        Load data from a specified group (prefix) - gps or gravity, from the projects HDF5 store.
        :param str uid: Datafile Unique Identifier
        :param str prefix: Data type prefix [gps or gravity]
        :return:
        """
        with HDFStore(self.hdf_path) as store:
            try:
                data = store.get('{}/{}'.format(prefix, uid))
            except KeyError:
                return None
            else:
                return data

    def add_data(self, packet: DataPacket):
        """
        Import a DataFrame into the project
        :param packet: DataPacket custom class containing file path, dataframe, data type and flight association
        :return: Void
        """
        self.log.debug("Ingesting data and exporting to hdf5 store")

        file_uid = 'f' + (uuid.uuid4().hex)[1:]  # Fix NaturalNameWarning by ensuring first char is letter ('f').

        with HDFStore(self.hdf_path) as store:
            # Separate data into groups by data type (GPS & Gravity Data)
            # format: 'table' pytables format enables searching/appending, fixed is more performant.
            store.put('{}/{}'.format(packet.data_type, file_uid), packet.data, format='fixed', data_columns=True)
            # Store a reference to the original file path
            self.data_map[file_uid] = packet.path
        try:
            flight = self.flights[packet.flight.uid]
            if packet.data_type == 'gravity':
                flight.gravity = file_uid
            elif packet.data_type == 'gps':
                flight.gps = file_uid
        except KeyError:
            return False

    def add_flight(self, flight: Flight):
        self.flights[flight.uid] = flight

    def get_flight(self, flight_id):
        flt = self.flights.get(flight_id, None)
        self.log.debug("Found flight {}:{}".format(flt.name, flt.uid))
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
            fli_item.setData(flight, QtCore.Qt.UserRole)

            gps_path, gps_uid = flight.gps_file
            gps = QStandardItem("GPS UID: {}".format(gps_uid))
            gps.setToolTip("File Path: {}".format(gps_path))
            gps.setEditable(False)
            gps.setData(gps_uid)  # For future use

            grav_path, grav_uid = flight.gravity_file
            grav = QStandardItem("Gravity: {}".format(grav_uid))
            grav.setToolTip("File Path: {}".format(grav_path))
            grav.setEditable(False)
            grav.setData(grav_uid)  # For future use

            fli_item.appendRow(gps)
            fli_item.appendRow(grav)

            for line in flight:
                line_item = QStandardItem("Line {}:{}".format(line.start, line.end))
                line_item.setEditable(False)
                fli_item.appendRow(line_item)
            fli_header.appendRow(fli_item)
        prj_header.appendRow(fli_header)

        root.appendRow(prj_header)
        self.log.debug("Tree Model generated")
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
