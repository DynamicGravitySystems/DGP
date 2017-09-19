# coding: utf-8

import os
import uuid
import pickle
import pathlib
import logging

from pandas import HDFStore, DataFrame, Series

from dgp.lib.meterconfig import MeterConfig, AT1Meter
from dgp.lib.types import Location, StillReading, FlightLine, DataPacket
import dgp.lib.eotvos as eov

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
    if isinstance(attribute, DataFrame):
        return False
    return True


class GravityProject:
    """
    GravityProject will be the base class defining common values for both airborne
    and marine gravity survey projects.
    """
    version = 0.1  # Used for future pickling compatability

    def __init__(self, path: pathlib.Path, name: str="Untitled Project", description: str=None):
        """
        Initializes a new GravityProject project class

        Parameters
        ----------
        path : pathlib.Path
            Directory which will be used to store project configuration and data files.
        name : str
            Human readable name to call this project.
        description : str
            Short description for this project.
        """
        self.log = logging.getLogger(__name__)
        if isinstance(path, pathlib.Path):
            self.projectdir = path  # type: pathlib.Path
        else:
            self.projectdir = pathlib.Path(path)
        if not self.projectdir.exists():
            raise FileNotFoundError

        if not self.projectdir.is_dir():
            raise NotADirectoryError

        self.name = name
        self.description = description

        # self.hdf_path = os.path.join(self.projectdir, 'prjdata.h5')
        self.hdf_path = self.projectdir.joinpath('prjdata.h5')

        # Store MeterConfig objects in dictionary keyed by the meter name
        self._sensors = {}

        self.log.debug("Gravity Project Initialized")

    def load_data(self, uid: str, prefix: str):
        """
        Load data from the project HDFStore (HDF5 format datafile) by prefix and uid.

        Parameters
        ----------
        uid : str
            32 digit hexadecimal unique identifier for the file to load.
        prefix : str
            Data type prefix, 'gps' or 'gravity' specifying the HDF5 group to retrieve the file from.

        Returns
        -------
        DataFrame
            Pandas DataFrame retrieved from HDFStore
        """
        self.log.info("Loading data <{}>/{} from HDFStore".format(prefix, uid))
        with HDFStore(str(self.hdf_path)) as store:
            try:
                data = store.get('{}/{}'.format(prefix, uid))
            except KeyError:
                self.log.warning("No data exists for key: {}".format(uid))
                return None
            else:
                return data

    def add_meter(self, meter: MeterConfig) -> MeterConfig:
        """Add an existing MeterConfig class to the dictionary of available meters"""
        if isinstance(meter, MeterConfig):
            self._sensors[meter.name] = meter
            return self._sensors[meter.name]
        else:
            raise ValueError("meter parameter is not an instance of MeterConfig")

    def get_meter(self, name):
        return self._sensors.get(name, None)

    def import_meter(self, path: pathlib.Path):
        """Import a meter configuration from an ini file and add it to the sensors dict"""
        # TODO: Way to construct different meter types (other than AT1 meter) dynamically
        if path.exists():
            try:
                meter = AT1Meter.from_ini(path)
                self._sensors[meter.name] = meter
            except ValueError:
                raise ValueError("Meter .ini file could not be imported, check format.")
            else:
                return self._sensors[meter.name]
        else:
            raise OSError("Path {} doesn't exist.".format(path))

    @property
    def meters(self):
        """Return list of meter names assigned to this project."""
        for meter in self._sensors.values():
            yield meter

    def save(self, path: pathlib.Path=None):
        """
        Saves the project by pickling the project class and saving to a file specified by path.

        Parameters
        ----------
        path : pathlib.Path, optional
            Optional path object to manually specify the save location for the project class object. By default if no
            path is passed to the save function, the project will be saved in the projectdir directory in a file named
            for the project name, with extension .d2p

        Returns
        -------
        bool
            True if successful

        """
        if path is None:
            path = self.projectdir.joinpath('{}.d2p'.format(self.name))
        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)
        with path.open('wb') as f:
            pickle.dump(self, f)
        return True

    @staticmethod
    def load(path: pathlib.Path):
        """
        Loads an existing project by unpickling a previously pickled project class from a file specified by path.

        Parameters
        ----------
        path : pathlib.Path
            Path object referencing the binary file containing a pickled class object e.g. Path(project.d2p).

        Returns
        -------
        GravityProject
            Unpickled GravityProject (or descendant) object.

        Raises
        ------
        FileNotFoundError
            If path does not exist.

        """
        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)
        if not path.exists():
            raise FileNotFoundError

        with path.open('rb') as pickled:
            project = pickle.load(pickled)
            # Override whatever the project dir was with the directory where it was opened
            project.projectdir = path.parent
        return project

    def __iter__(self):
        pass

    def __getstate__(self):
        """
        Used by the python pickle.dump method to determine if a class __dict__ member is 'pickleable'

        Returns
        -------
        dict
            Dictionary of self.__dict__ items that have been filtered using the can_pickle() function.
        """
        return {k: v for k, v in self.__dict__.items() if can_pickle(v)}

    def __setstate__(self, state) -> None:
        """
        Used to adjust state of the class upon loading using pickle.load. This is used to reinitialize class
        attributes that could not be pickled (filtered out using __getstate__).
        In future this method may be used to ensure backwards compatibility with older version project classes that
        are loaded using a newer software/project version.

        Parameters
        ----------
        state
            Input state passed by the pickle.load function

        Returns
        -------
        None
        """
        self.__dict__.update(state)
        self.log = logging.getLogger(__name__)


class Flight:
    """
    Define a Flight class used to record and associate data with an entire survey flight (takeoff -> landing)
    This class is iterable, yielding the flightlines named tuple objects from its lines dictionary
    """
    def __init__(self, parent: GravityProject, name: str, meter: MeterConfig=None, **kwargs):
        """
        The Flight object represents a single literal survey flight (Takeoff -> Landing) and stores various
        parameters and configurations related to the flight.
        The Flight class provides an easy interface to retrieve GPS and Gravity data which has been associated with it
        in the project class.
        Currently a Flight tracks a single GPS and single Gravity data file, if a second file is subsequently imported
        the reference to the old file will be overwritten.
        In future we plan on expanding the functionality so that multiple data files might be assigned to a flight, with
        various operations (comparison, merge, join) able to be performed on them.

        Parameters
        ----------
        parent : GravityProject
            Parent project class which this flight belongs to. This is essential as the project stores the references
            to all data files which the flight may rely upon.
        name : str
            Human-readable reference name for this flight.
        meter : MeterConfig
            Gravity Meter configuration to assign to this flight.
        kwargs
            Arbitrary keyword arguments.
            uuid : uuid.uuid
                Unique identifier to assign to this flight, else a uuid will be generated upon creation using the
                uuid.uuid4() method.
            date : datetime.date
                Datetime object to  assign to this flight.
        """
        # If uuid is passed use the value else assign new uuid
        # the letter 'f' is prepended to the uuid to ensure that we have a natural python name
        # as python variables cannot start with a number (this takes care of warning when storing data in pytables)
        self.parent = parent
        self.name = name
        self.uid = kwargs.get('uuid', self.generate_uuid())
        self.meter = meter
        if 'date' in kwargs:
            print("Setting date to: {}".format(kwargs['date']))
            self.date = kwargs['date']

        self.log = logging.getLogger(__name__)

        # These private attributes will hold a file reference string used to retrieve data from hdf5 store.
        self._gpsdata_uid = None  # type: str
        self._gravdata_uid = None  # type: str

        self._gpsdata = None  # type: DataFrame
        self._gravdata = None  # type: DataFrame

        # Known Absolute Site Reading/Location
        self.tie_value = None
        self.tie_location = None

        self.pre_still_reading = None
        self.post_still_reading = None

        self.flight_timeshift = 0

        # Flight lines keyed by UUID
        self.lines = {}

    @property
    def gps(self):
        if self._gpsdata_uid is None:
            return
        if self._gpsdata is None:
            self.log.warning("Loading gps data from HDFStore.")
            self._gpsdata = self.parent.load_data(self._gpsdata_uid, 'gps')
        return self._gpsdata

    @gps.setter
    def gps(self, value):
        if self._gpsdata_uid:
            self.log.warning('GPS Data File already exists, overwriting with new value.')
            self._gpsdata = None
        self._gpsdata_uid = value

    @property
    def gps_file(self):
        try:
            return self.parent.data_map[self._gpsdata_uid], self._gpsdata_uid
        except KeyError:
            return None, None

    @property
    def gravity(self):
        """
        Property accessor for Gravity data. This accessor will cache loaded
        gravity data in an instance variable so that subsequent lookups do
        not require an I/O operation.
        Returns
        -------
        DataFrame
            pandas DataFrame containing Gravity Data
        """
        if self._gravdata_uid is None:
            return
        if self._gravdata is None:
            self.log.warning("Loading gravity data from HDFStore.")
            self._gravdata = self.parent.load_data(self._gravdata_uid,
                                                   'gravity')
        return self._gravdata

    @gravity.setter
    def gravity(self, value):
        if self._gravdata_uid:
            self.log.warning('Gravity Data File already exists, overwriting with new value.')
            self._gravdata = None
        self._gravdata_uid = value

    @property
    def gravity_file(self):
        try:
            return self.parent.data_map[self._gravdata_uid], self._gravdata_uid
        except KeyError:
            return None, None

    @property
    def eotvos(self):
        if self.gps is None:
            return None
        gps_data = self.gps
        lat = gps_data['lat']
        lon = gps_data['long']
        ht = gps_data['ell_ht']
        rate = 10
        ev_corr = eov.calc_eotvos(lat, lon, ht, rate, eov.derivative)
        # ev_series = Series(ev_corr, index=lat.index, name='eotvos')
        # return ev_series
        return ev_corr

    def get_channel_data(self, channel):
        return self.gravity[channel]

    def add_line(self, start: float, end: float):
        """Add a flight line to the flight by start/stop index and sequence number"""
        uid = uuid.uuid4().hex
        line = FlightLine(uid, len(self.lines), None, start, end)
        self.lines[uid] = line
        return line

    @staticmethod
    def generate_uuid():
        """
        Generates a Universally Unique ID (UUID) using the uuid.uuid4() method, and replaces the first hex digit with
        'f' to ensure the UUID conforms to python's Natural Name convention, simply meaning that the name does not start
        with a number, as this raises warnings when using the UUID as a key in a Pandas dataframe or when exporting data
        to an HDF5 store.

        Returns
        -------
        str
            32 digit hexadecimal string unique identifier where str[0] == 'f'
        """
        return 'f{}'.format(uuid.uuid4().hex[1:])

    def __iter__(self):
        """
        Implement class iteration, allowing iteration through FlightLines in this Flight
        Yields
        -------
        FlightLine : NamedTuple
            Next FlightLine in Flight.lines
        """
        for k, line in self.lines.items():
            yield line

    def __len__(self):
        return len(self.lines)

    def __repr__(self):
        return "<Flight {parent}, {name}, {meter}>".format(parent=self.parent, name=self.name,
                                                           meter=self.meter)

    def __str__(self):
        if self.meter is not None:
            mname = self.meter.name
        else:
            mname = '<None>'
        desc = """Flight: {name}\n
UID: {uid}
Meter: {meter}
# Lines: {lines}
Data Files:
        """.format(name=self.name, uid=self.uid, meter=mname, lines=len(self))
        return desc

    def __getstate__(self):
        return {k: v for k, v in self.__dict__.items() if can_pickle(v)}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.log = logging.getLogger(__name__)
        self._gravdata = None
        self._gpsdata = None


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

    def add_data(self, packet: DataPacket, flight_uid: str):
        """
        Add a DataPacket to the project.
        The DataPacket is simply a container for a pandas.DataFrame object, containing some additional meta-data that is
        used by the project and interface.
        Upon adding a DataPacket, the DataFrame is assigned a UUID and together with the data type, is exported to the
        projects' HDFStore into a group specified by data type i.e.
            HDFStore.put('data_type/uuid', packet.data)
        The data can then be retrieved later from its respective group using its UUID.
        The UUID is then stored in the Flight class's data variable for the respective data_type.

        Parameters
        ----------
        packet : DataPacket(data, path, dtype)

        flight_uid : str


        Returns
        -------

        """
        """
        Import a DataFrame into the project
        :param packet: DataPacket custom class containing file path, dataframe, data type and flight association
        :return: Void
        """
        self.log.debug("Ingesting data and exporting to hdf5 store")

        file_uid = 'f' + uuid.uuid4().hex[1:]  # Fixes NaturalNameWarning by ensuring first char is letter ('f').

        with HDFStore(str(self.hdf_path)) as store:
            # Separate data into groups by data type (GPS & Gravity Data)
            # format: 'table' pytables format enables searching/appending, fixed is more performant.
            store.put('{}/{}'.format(packet.dtype, file_uid), packet.data, format='fixed', data_columns=True)
            # Store a reference to the original file path
            self.data_map[file_uid] = packet.path
        try:
            flight = self.flights[flight_uid]
            if packet.dtype == 'gravity':
                flight.gravity = file_uid
            elif packet.dtype == 'gps':
                flight.gps = file_uid
        except KeyError:
            return False

    def add_flight(self, flight: Flight):
        self.flights[flight.uid] = flight

    def get_flight(self, flight_id):
        flt = self.flights.get(flight_id, None)
        self.log.debug("Found flight {}:{}".format(flt.name, flt.uid))
        return flt

    def __iter__(self):
        for uid, flight in self.flights.items():
            yield flight

    def __len__(self):
        return len(self.flights)

    def __str__(self):
        return "Project: {name}\nPath: {path}\nDescription: {desc}".format(name=self.name,
                                                                           path=self.projectdir,
                                                                           desc=self.description)
