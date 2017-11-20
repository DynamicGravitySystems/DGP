# coding: utf-8

import pickle
import pathlib
import logging
from typing import Union, Type
from datetime import datetime

from pandas import HDFStore, DataFrame, Series

from dgp.gui.qtenum import QtItemFlags, QtDataRoles
from dgp.lib.meterconfig import MeterConfig, AT1Meter
from dgp.lib.etc import gen_uuid
from dgp.lib.types import FlightLine, TreeItem, DataFile, PlotCurve
import dgp.lib.eotvos as eov

"""
Dynamic Gravity Processor (DGP) :: project.py
License: Apache License V2

Overview:
project.py provides the object framework for setting up a gravity processing 
project, which may include project specific configurations and settings, 
project specific files and imports, and the ability to segment a project into 
individual flights and flight lines.

Guiding Principles:
This module has been designed to be explicitly independant of Qt, primarly 
because it is tricky or impossible to pickle many Qt objects. This also in 
theory means that the classes contained within can be utilized for other uses, 
without relying on the specific Qt GUI package.
Because of this, some abstraction has been necesarry particulary in the 
models.py class, which acts as a bridge between the Classes in this module, 
and the Qt GUI - providing the required interfaces to display and interact with 
the project from a graphical user interface (Qt).
Though there is no dependence on Qt itself, there are a few methods e.g. the 
data() method in several classes, that are particular to our Qt GUI - 
specifically they return internal data based on a 'role' parameter, which is 
simply an int passed by a Qt Display Object telling the underlying code which 
data is being requested for a particular display type.

Workflow:
    User creates new project - enters project name, description, and location to 
    save project.
        - User can additionaly define survey parameters specific to the project
        - User can then add a Gravity Meter configuration to the project
        - User then creates new flights each day a flight is flown, flight 
        parameters are defined
        - Data files are imported into project and associated with a flight
            - Upon import the file will be converted to pandas DataFrame then 
            written out to the project directory as HDF5.
        - User selects between flights in GUI to view in plot, data is pulled 
        from the Flight object

"""


def can_pickle(attribute):
    """Helper function used by __getstate__ to determine if an attribute
    can/should be pickled."""
    no_pickle = [logging.Logger, DataFrame]
    for invalid in no_pickle:
        if isinstance(attribute, invalid):
            return False
    if attribute.__class__.__name__ == 'ProjectModel':
        return False
    return True


class GravityProject(TreeItem):
    """
    GravityProject will be the base class defining common values for both
    airborne and marine gravity survey projects.
    """
    version = 0.2  # Used for future pickling compatibility

    def __init__(self, path: pathlib.Path, name: str="Untitled Project",
                 description: str=None, model_parent=None):
        """
        Initializes a new GravityProject project class

        Parameters
        ----------
        path : pathlib.Path
            Directory which will be used to store project configuration and data
        name : str
            Human readable name to call this project.
        description : str
            Short description for this project.
        """
        super().__init__(gen_uuid('prj'), parent=None)
        self._model_parent = model_parent
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

    def data(self, role: QtDataRoles):
        if role == QtDataRoles.DisplayRole:
            return self.name
        return None

    @property
    def model(self):
        return self._model_parent

    @model.setter
    def model(self, value):
        self._model_parent = value

    def load_data(self, uid: str, prefix: str = 'data'):
        """
        Load data from the project HDFStore (HDF5 format datafile) by uid.

        Parameters
        ----------
        uid : str
            32 digit hexadecimal unique identifier for the file to load.
        prefix : str
            Deprecated - parameter reserved while testing compatibility
            Data type prefix, 'gps' or 'gravity' specifying the HDF5 group to
            retrieve the file from.

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
        """Add an existing MeterConfig class to the dictionary of meters"""
        if isinstance(meter, MeterConfig):
            self._sensors[meter.name] = meter
            return self._sensors[meter.name]
        else:
            raise ValueError("meter param is not an instance of MeterConfig")

    def get_meter(self, name):
        return self._sensors.get(name, None)

    def import_meter(self, path: pathlib.Path):
        """Import a meter config from ini file and add it to the sensors dict"""
        # TODO: Need to construct different meter types (other than AT1 meter)
        if path.exists():
            try:
                meter = AT1Meter.from_ini(path)
                self._sensors[meter.name] = meter
            except ValueError:
                raise ValueError("Meter .ini file could not be imported, check "
                                 "format.")
            else:
                return self._sensors[meter.name]
        else:
            raise OSError("Path {} doesn't exist.".format(path))

    @property
    def meters(self):
        """Return list of meter names assigned to this project."""
        for meter in self._sensors.values():
            yield meter

    def save(self, path: pathlib.Path = None):
        """
        Saves the project by pickling the project class and saving to a file
        specified by path.

        Parameters
        ----------
        path : pathlib.Path, optional
            Optional path object to manually specify the save location for the
            project class object. By default if no path is passed to the save
            function, the project will be saved in the projectdir directory in a
            file named for the project name, with extension .d2p

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
        Loads an existing project by unpickling a previously pickled project
        class from a file specified by path.

        Parameters
        ----------
        path : pathlib.Path
            Path object referencing the binary file containing a pickled class
            object e.g. Path(project.d2p).

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
            # Update project directory in case project was moved
            project.projectdir = path.parent
        return project

    def __iter__(self):
        raise NotImplementedError("Abstract definition, not implemented.")

    def __getstate__(self):
        """
        Used by the python pickle.dump method to determine if a class __dict__
        member is 'pickleable'

        Returns
        -------
        dict
            Dictionary of self.__dict__ items that have been filtered using the
            can_pickle() function.
        """
        return {k: v for k, v in self.__dict__.items() if can_pickle(v)}

    def __setstate__(self, state) -> None:
        """
        Used to adjust state of the class upon loading using pickle.load. This
        is used to reinitialize class
        attributes that could not be pickled (filtered out using __getstate__).
        In future this method may be used to ensure backwards compatibility with
        older version project classes that are loaded using a newer
        software/project version.

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
    Define a Flight class used to record and associate data with an entire
    survey flight (takeoff -> landing)
    This class is iterable, yielding the flightlines named tuple objects from
    its lines dictionary
    """

    def __init__(self, project: GravityProject, name: str,
                 meter: MeterConfig = None, **kwargs):
        """
        The Flight object represents a single literal survey flight
        (Takeoff -> Landing) and stores various parameters and configurations
        related to the flight.
        The Flight class provides an easy interface to retrieve GPS and Gravity
        data which has been associated with it in the project class.
        Currently a Flight tracks a single GPS and single Gravity data file, if
        a second file is subsequently imported the reference to the old file
        will be overwritten.
        In future we plan on expanding the functionality so that multiple data
        files might be assigned to a flight, with various operations
        (comparison, merge, join) able to be performed on them.

        Parameters
        ----------
        parent : GravityProject
            Parent project class which this flight belongs to. This is essential
             as the project stores the references to all data files which the
             flight may rely upon.
        name : str
            Human-readable reference name for this flight.
        meter : MeterConfig
            Gravity Meter configuration to assign to this flight.
        kwargs
            Arbitrary keyword arguments.
            uuid : uuid.uuid
                Unique identifier to assign to this flight, else a uuid will be
                generated upon creation using the
                uuid.uuid4() method.
            date : datetime.date
                Datetime object to  assign to this flight.
        """
        self.log = logging.getLevelName(__name__)
        uid = kwargs.get('uuid', gen_uuid('flt'))
        super().__init__(uid, parent=None)

        self.name = name
        self._project = project
        self._icon = ':images/assets/flight_icon.png'
        self.style = {'icon': ':images/assets/flight_icon.png',
                      QtDataRoles.BackgroundRole: 'LightGray'}
        self.meter = meter
        if 'date' in kwargs:
            print("Setting date to: {}".format(kwargs['date']))
            self.date = kwargs['date']
        else:
            self.date = "No date set"

        self.log = logging.getLogger(__name__)

        # These attributes will hold a file reference string used to retrieve
        # data from hdf5 store.
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

        # Issue #36 Plotting data channels
        self._channels = {}  # {uid: (file_uid, label), ...}
        self._plotted_channels = {}  # {uid: axes_index, ...}
        self._default_plot_map = {'gravity': 0, 'long': 1, 'cross': 1}

        self._data_cache = {}  # {data_uid: DataFrame, ...}

        self._lines = Container(ctype=FlightLine, parent=self,
                                name='Flight Lines')
        self._data = Container(ctype=DataFile, parent=self, name='Data Files')
        self.append_child(self._lines)
        self.append_child(self._data)

    def data(self, role):
        if role == QtDataRoles.ToolTipRole:
            return "<{name}::{uid}>".format(name=self.name, uid=self.uid)
        if role == QtDataRoles.DisplayRole:
            return "{name} - {date}".format(name=self.name, date=self.date)
        return super().data(role)

    @property
    def lines(self):
        return self._lines

    @property
    def gps(self):
        if self._gpsdata_uid is None:
            return
        if self._gpsdata is None:
            self.log.warning("Loading gps data from HDFStore.")
            self._gpsdata = self._project.load_data(self._gpsdata_uid)
        return self._gpsdata

    @gps.setter
    def gps(self, value):
        if self._gpsdata_uid:
            self.log.warning('GPS Data File already exists, overwriting with '
                             'new value.')
            self._gpsdata = None
        self._gpsdata_uid = value

    @property
    def gps_file(self):
        try:
            return self._project.data_map[self._gpsdata_uid], self._gpsdata_uid
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
            return None
        if self._gravdata is None:
            self.log.warning("Loading gravity data from HDFStore.")
            self._gravdata = self._project.load_data(self._gravdata_uid)
        return self._gravdata

    @gravity.setter
    def gravity(self, value):
        if self._gravdata_uid:
            self.log.warning(
                'Gravity Data File already exists, overwriting with new value.')
            self._gravdata = None
        self._gravdata_uid = value

    @property
    def gravity_file(self):
        try:
            return self._project.data_map[self._gravdata_uid], \
                   self._gravdata_uid
        except KeyError:
            return None, None

    @property
    def eotvos(self):
        if self.gps is None:
            return None
        gps_data = self.gps
        # WARNING: It is vital to use the .values of the pandas Series,
        # otherwise the eotvos func does not work properly for some reason
        index = gps_data['lat'].index
        lat = gps_data['lat'].values
        lon = gps_data['long'].values
        ht = gps_data['ell_ht'].values
        rate = 10
        ev_corr = eov.calc_eotvos(lat, lon, ht, rate)
        ev_frame = DataFrame(ev_corr, index=index, columns=['eotvos'])
        return ev_frame

    @property
    def channels(self):
        """Return data channels as map of {uid: label, ...}"""
        return {k: self._channels[k][1] for k in self._channels}

    def update_series(self, line: PlotCurve, action: str):
        """Update the Flight state tracking for plotted data channels"""
        self.log.info(
            "Doing {action} on line {line} in {flt}".format(action=action,
                                                            line=line.label,
                                                            flt=self.name))
        if action == 'add':
            self._plotted_channels[line.uid] = line.axes
        elif action == 'remove':
            try:
                del self._plotted_channels[line.uid]
            except KeyError:
                self.log.error("No plotted line to remove")

    def get_plot_state(self):
        # Return: {uid: (label, axes), ...}
        state = {}
        # TODO: Could refactor into dict comp
        for uid in self._plotted_channels:
            state[uid] = self._channels[uid][1], self._plotted_channels[uid]
        return state

    def get_channel_data(self, uid: str):
        data_uid, field = self._channels[uid]
        if data_uid in self._data_cache:
            return self._data_cache[data_uid][field]
        else:
            self.log.warning(
                "Loading datafile {} from HDF5 Store".format(data_uid))
            self._data_cache[data_uid] = self._project.load_data(data_uid)
            return self.get_channel_data(uid)

    def add_data(self, data: DataFile):
        self._data.append_child(data)

        for col in data.fields:
            col_uid = gen_uuid('col')
            self._channels[col_uid] = data.uid, col
            # If defaults are specified then add them to the plotted_channels
            if col in self._default_plot_map:
                self._plotted_channels[col_uid] = self._default_plot_map[col]
        # print("Plotted: ", self._plotted_channels)
        # print(self._channels)

    def add_line(self, start: datetime, stop: datetime, uid=None):
        """Add a flight line to the flight by start/stop index and sequence
        number"""
        # line = FlightLine(len(self.lines), None, start, end, self)
        self.log.debug(
            "Adding line to LineContainer of flight: {}".format(self.name))
        line = FlightLine(start, stop, len(self._lines) + 1, None, uid=uid,
                          parent=self.lines)
        self._lines.append_child(line)
        # self.update('add', line)
        return line

    def remove_line(self, uid):
        """ Remove a flight line """
        line = self._lines[uid]
        self._lines.remove_child(self._lines[uid])
        # self.update('del', line)

    def clear_lines(self):
        """Removes all Lines from Flight"""
        return
        self._lines.clear()

    def __iter__(self):
        """
        Implement class iteration, allowing iteration through FlightLines
        Yields
        -------
        FlightLine : NamedTuple
            Next FlightLine in Flight.lines
        """
        for line in self._lines:
            yield line

    def __len__(self):
        return len(self._lines)

    def __repr__(self):
        return "{cls}({parent}, {name}, {meter})".format(
            cls=type(self).__name__,
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
    # Arbitrary list of permitted types
    ctypes = {Flight, MeterConfig, FlightLine, DataFile}

    def __init__(self, ctype, parent, *args, **kwargs):
        """
        Defines a generic container designed for use with models.ProjectModel,
        implementing the required functions to display and contain child
        objects.
        When used/displayed by a TreeView the default behavior is to display the
        ctype.__name__ and a tooltip stating "Container for <name> type
        objects".

        The Container contains only objects of type ctype, or those derived from
        it. Attempting to add a child of a different type will simply fail,
        with the add_child method returning
        False.
        Parameters
        ----------
        ctype : Class
            The object type this container will contain as children, permitted
            classes are:
            Flight
            FlightLine
            MeterConfig
        parent
            Parent object, e.g. Gravity[Airborne]Project, Flight etc. The
            container will set the 'parent' attribute of any children added
            to the container to this value.
        args : [List<ctype>]
            Optional child objects to add to the Container at instantiation
        kwargs
            Optional key-word arguments. Recognized values:
            str name : override the default name of this container (which is
            _ctype.__name__)
        """
        super().__init__(uid=gen_uuid('box'), parent=parent)
        assert ctype in Container.ctypes
        # assert parent is not None
        self._ctype = ctype
        self._name = kwargs.get('name', self._ctype.__name__)
        _icon = ':/images/assets/folder_open.png'
        self.style = {QtDataRoles.DecorationRole: _icon,
                      QtDataRoles.BackgroundRole: 'LightBlue'}

    @property
    def ctype(self):
        return self._ctype

    @property
    def name(self):
        return self._name.lower()

    def data(self, role: QtDataRoles):
        if role == QtDataRoles.ToolTipRole:
            return "Container for {} objects. <{}>".format(self._name, self.uid)
        if role == QtDataRoles.DisplayRole:
            return self._name
        return super().data(role)

    def append_child(self, child) -> None:
        """
        Add a child object to the container.
        The child object must be an instance of the ctype of the container,
        otherwise it will be rejected.
        Parameters
        ----------
        child
            Child object of compatible type <ctype> for this container.
        Raises
        ------
        TypeError:
            Raises TypeError if child is not of the permitted type defined by
            this container.
        """
        if not isinstance(child, self._ctype):
            raise TypeError("Child type is not permitted in this container.")
        super().append_child(child)

    def __str__(self):
        # return self._name
        return str(self._children)


class AirborneProject(GravityProject):
    """
    A subclass of the base GravityProject, AirborneProject will define an
    Airborne survey project with parameters unique to airborne operations,
    and defining flight lines etc.

    This class is iterable, yielding the Flight objects contained within its
    flights dictionary
    """

    def __iter__(self):
        pass

    def __init__(self, path: pathlib.Path, name, description=None, parent=None):
        super().__init__(path, name, description)

        self._flights = Container(ctype=Flight, name="Flights", parent=self)
        self.append_child(self._flights)
        self._meters = Container(ctype=MeterConfig, name="Meter Configurations",
                                 parent=self)
        self.append_child(self._meters)

        self.log.debug("Airborne project initialized")
        self.data_map = {}
        # print("Project children:")
        # for child in self.children:
        #     print(child.uid)

    def data(self, role: QtDataRoles):
        if role == QtDataRoles.DisplayRole:
            return "{} :: <{}>".format(self.name, self.projectdir.resolve())
        return super().data(role)

    # TODO: Move this into the GravityProject base class?
    # Although we use flight_uid here, this could be abstracted.
    def add_data(self, df: DataFrame, path: pathlib.Path, dtype: str,
                 flight_uid: str):
        """
        Add an imported DataFrame to a specific Flight in the project.
        Upon adding a DataFrame a UUID is assigned, and together with the data
        type it is exported to the project HDFStore into a group specified by
        data type i.e.
                HDFStore.put('data_type/uuid', packet.data)
        The data can then be retrieved from its respective dtype group using the
        UUID. The UUID is then stored in the Flight class's data variable for
        the respective data_type.

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
        file_uid = gen_uuid('dat')

        with HDFStore(str(self.hdf_path)) as store:
            # format: 'table' pytables format enables searching/appending,
            # fixed is more performant.
            store.put('data/{uid}'.format(uid=file_uid), df, format='fixed',
                      data_columns=True)
            # Store a reference to the original file path
            self.data_map[file_uid] = path
        try:
            flight = self.get_flight(flight_uid)

            flight.add_data(
                DataFile(file_uid, path, [col for col in df.keys()], dtype))
            if dtype == 'gravity':
                if flight.gravity is not None:
                    print("Clearing old FlightLines")
                    flight.clear_lines()
                flight.gravity = file_uid
            elif dtype == 'gps':
                flight.gps = file_uid
            return True
        except KeyError:
            return False

    def update(self, **kwargs):
        """Used to update the wrapping (parent) ProjectModel of this project for
         GUI display"""
        if self.model is not None:
            # print("Calling update on parent model with params: {} {}".format(
            #     action, item))
            self.model.update(**kwargs)

    def add_flight(self, flight: Flight) -> None:
        flight.parent = self
        self._flights.append_child(flight)

        # self._children['flights'].add_child(flight)
        # self.update('add', flight)

    def remove_flight(self, flight: Flight) -> bool:
        self._flights.remove_child(flight)
        # self.update('del', flight, parent=flight.parent, row=flight.row())

    def get_flight(self, uid):
        return self._flights.child(uid)

    @property
    def count_flights(self):
        return len(self._flights)

    @property
    def flights(self):
        for flight in self._flights:
            yield flight
