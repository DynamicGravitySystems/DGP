# coding: utf-8

import uuid
import pickle
import pathlib
import logging
from typing import Union, Type
from datetime import datetime

from pandas import HDFStore, DataFrame, Series

from dgp.lib.meterconfig import MeterConfig, AT1Meter
from dgp.lib.etc import gen_uuid
from dgp.lib.types import Location, StillReading, FlightLine, TreeItem
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

# QT ItemDataRoles
DisplayRole = 0
DecorationRole = 1
ToolTipRole = 3
StatusTipRole = 4
UserRole = 256


def can_pickle(attribute):
    """Helper function used by __getstate__ to determine if an attribute should be pickled."""
    # TODO: As necessary change this to check against a list of un-pickleable types
    no_pickle = [logging.Logger, DataFrame]
    for invalid in no_pickle:
        if isinstance(attribute, invalid):
            return False
    if attribute.__class__.__name__ == 'ProjectModel':
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
        raise NotImplementedError("Abstract definition, not implemented.")

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


class Flight(TreeItem):
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
        # as python variables cannot start with a number
        self._parent = parent
        self.name = name
        self._uid = kwargs.get('uuid', gen_uuid('f'))
        self._icon = ':images/assets/flight_icon.png'
        self.meter = meter
        if 'date' in kwargs:
            print("Setting date to: {}".format(kwargs['date']))
            self.date = kwargs['date']

        self.log = logging.getLogger(__name__)

        # These attributes will hold a file reference string used to retrieve data from hdf5 store.
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

        self.lines = Container(ctype=FlightLine, parent=self, name='Flight Lines')

    @property
    def uid(self):
        return self._uid

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value

    def data(self, role=None):
        if role == UserRole:
            return self
        if role == ToolTipRole:
            return repr(self)
        if role == DecorationRole:
            return self._icon
        return self.name

    @property
    def children(self):
        """Yield appropriate child objects for display in project Tree View"""
        for child in [self.lines, self._gpsdata_uid, self._gravdata_uid]:
            yield child

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
        # WARNING: It is vital to use the .values of the pandas Series, otherwise the eotvos func
        # does not work properly for some reason
        # TODO: Find out why that is ^
        index = gps_data['lat'].index
        lat = gps_data['lat'].values
        lon = gps_data['long'].values
        ht = gps_data['ell_ht'].values
        rate = 10
        ev_corr = eov.calc_eotvos(lat, lon, ht, rate)
        ev_frame = DataFrame(ev_corr, index=index, columns=['eotvos'])
        return ev_frame

    def get_channel_data(self, channel):
        return self.gravity[channel]

    def add_line(self, start: datetime, stop: datetime, uid=None):
        """Add a flight line to the flight by start/stop index and sequence number"""
        # line = FlightLine(len(self.lines), None, start, end, self)
        self.log.debug("Adding line to LineContainer of flight: {}".format(self.name))
        print("Adding line to LineContainer of flight: {}".format(self.name))
        line = FlightLine(start, stop, len(self.lines) + 1, None, uid=uid, parent=self)
        self.lines.add_child(line)
        self.parent.update('add', line, self.lines.uid)
        return line

    def remove_line(self, uid):
        """ Remove a flight line """
        return self.lines.remove_child(self.lines[uid])

    def __iter__(self):
        """
        Implement class iteration, allowing iteration through FlightLines in this Flight
        Yields
        -------
        FlightLine : NamedTuple
            Next FlightLine in Flight.lines
        """
        for line in self.lines:
            yield line

    def __len__(self):
        return len(self.lines)

    def __repr__(self):
        return "{cls}({parent}, {name}, {meter})".format(cls=type(self).__name__,
                                                         parent=self.parent, name=self.name,
                                                         meter=self.meter)

    def __str__(self):
        return "Flight: {name}".format(name=self.name)

    def __getstate__(self):
        return {k: v for k, v in self.__dict__.items() if can_pickle(v)}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.log = logging.getLogger(__name__)
        self._gravdata = None
        self._gpsdata = None


class Container(TreeItem):
    ctypes = {Flight, MeterConfig, FlightLine}

    def __init__(self, ctype, parent, *args, **kwargs):
        """
        Defines a generic container designed for use with models.ProjectModel, implementing the
        required functions to display and contain child objects.
        When used/displayed by a TreeView the default behavior is to display the ctype.__name__
        and a tooltip stating "Container for <name> type objects".

        The Container contains only objects of type ctype, or those derived from it. Attempting
        to add a child of a different type will simply fail, with the add_child method returning
        False.
        Parameters
        ----------
        ctype : Class
            The object type this container will contain as children, permitted classes are:
            Flight
            FlightLine
            MeterConfig
        parent
            Parent object, e.g. Gravity[Airborne]Project, Flight etc. The container will set the
            'parent' attribute of any children added to the container to this value.
        args : [List<ctype>]
            Optional child objects to add to the Container at instantiation
        kwargs
            Optional key-word arguments. Recognized values:
            str name : override the default name of this container (which is _ctype.__name__)
        """
        assert ctype in Container.ctypes
        # assert parent is not None
        self._uid = gen_uuid('c')
        self._parent = parent
        self._ctype = ctype
        self._name = kwargs.get('name', self._ctype.__name__)
        self._children = {}
        for arg in args:
            self.add_child(arg)

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value

    @property
    def ctype(self):
        return self._ctype

    @property
    def uid(self):
        return self._uid

    @property
    def name(self):
        return self._name.lower()

    @property
    def children(self):
        for flight in self._children:
            yield self._children[flight]

    def data(self, role=None):
        if role == ToolTipRole:
            return "Container for {} type objects.".format(self._name)
        return self._name

    # TODO: Implement recursive search function to locate child/object by UID in the tree.

    def child(self, uid):
        return self._children[uid]

    def add_child(self, child) -> bool:
        """
        Add a child object to the container.
        The child object must be an instance of the ctype of the container, otherwise it will be rejected.
        Parameters
        ----------
        child
            Child object of compatible type <ctype> for this container.
        Returns
        -------
        bool:
            True if add is sucessful
            False if add fails (e.g. child is not a valid type for this container)
        """
        if not isinstance(child, self._ctype):
            return False
        if child.uid in self._children:
            print("child {} already exists in container, skipping insert".format(child))
            return True
        try:
            child.parent = self._parent
        except AttributeError:
            # Can't reassign tuple attribute (may change FlightLine to class in future)
            pass
        self._children[child.uid] = child
        return True

    def __getitem__(self, key):
        return self._children[key]

    def __contains__(self, key):
        return key in self._children

    def remove_child(self, child) -> bool:
        """
        Remove a child object from the container.
        Children are deleted by the uid key, no other comparison is executed.
        Parameters
        ----------
        child

        Returns
        -------
        bool:
            True on sucessful deletion of child
            False if child.uid could not be retrieved and deleted
        """
        try:
            del self._children[child.uid]
            print("Deleted obj uid: {} from container children".format(child.uid))
            return True
        except KeyError:
            return False

    def __iter__(self):
        for child in self._children.values():
            yield child

    def __len__(self):
        return len(self._children)

    def __str__(self):
        # return self._name
        return str(self._children)


class AirborneProject(GravityProject, TreeItem):
    """
    A subclass of the base GravityProject, AirborneProject will define an Airborne survey
    project with parameters unique to airborne operations, and defining flight lines etc.

    This class is iterable, yielding the Flight objects contained within its flights dictionary
    """
    def __init__(self, path: pathlib.Path, name, description=None, parent=None):
        super().__init__(path, name, description)

        self._parent = parent
        # Dictionary of Flight objects keyed by the flight uuid
        self._children = {'flights': Container(ctype=Flight, parent=self),
                          'meters': Container(ctype=MeterConfig, parent=self)}
        self.log.debug("Airborne project initialized")
        self.data_map = {}

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value

    @property
    def children(self):
        for child in self._children:
            yield self._children[child]

    @property
    def uid(self):
        return

    def data(self, role=None):
        return "{} :: <{}>".format(self.name, self.projectdir.resolve())

    # TODO: Move this into the GravityProject base class?
    # Although we use flight_uid here, this could be abstracted however.
    def add_data(self, df: DataFrame, path: pathlib.Path, dtype: str, flight_uid: str):
        """
        Add an imported DataFrame to a specific Flight in the project.
        Upon adding a DataFrame a UUID is assigned, and together with the data type it is exported
        to the project HDFStore into a group specified by data type i.e.
            HDFStore.put('data_type/uuid', packet.data)
        The data can then be retrieved from its respective dtype group using the UUID.
        The UUID is then stored in the Flight class's data variable for the respective data_type.

        Parameters
        ----------
        df : DataFrame
            Pandas DataFrame containing file data.
        path : pathlib.Path
            Original path to data file as a pathlib.Path object.
        dtype : str
            The data type of the data (df) being added, either gravity or gps.
        flight_uid : str
            UUID of the Flight the added data will be assigned/associated with.

        Returns
        -------
        bool
            True on success, False on failure
            Causes of failure:
                flight_uid does not exist in self.flights.keys
        """
        self.log.debug("Ingesting data and exporting to hdf5 store")

        # Fixes NaturalNameWarning by ensuring first char is letter ('f').
        file_uid = 'f' + uuid.uuid4().hex[1:]

        with HDFStore(str(self.hdf_path)) as store:
            # Separate data into groups by data type (GPS & Gravity Data)
            # format: 'table' pytables format enables searching/appending, fixed is more performant.
            store.put('{typ}/{uid}'.format(typ=dtype, uid=file_uid), df, format='fixed', data_columns=True)
            # Store a reference to the original file path
            self.data_map[file_uid] = path
        try:
            flight = self.get_flight(flight_uid)
            if dtype == 'gravity':
                flight.gravity = file_uid
            elif dtype == 'gps':
                flight.gps = file_uid
            return True
        except KeyError:
            return False

    def update(self, action: str, item, uid=None) -> bool:
        if self.parent is not None:
            print("Calling update on parent model with params: {} {} {}".format(action, item, uid))
            self.parent.update(action, item, uid)
            return True
        return False

    def add_flight(self, flight: Flight) -> None:
        flight.parent = self
        self._children['flights'].add_child(flight)
        self.update('add', flight)

    def get_flight(self, uid):
        flight = self._children['flights'].child(uid)
        return flight

    @property
    def flights(self):
        for flight in self._children['flights'].children:
            yield flight

    def __iter__(self):
        return (i for i in self._children.items())

    def __len__(self):
        count = 0
        for child in self._children:
            count += len(child)
        return count

    def __str__(self):
        return "AirborneProject: {}".format(self.name)
