# coding: utf-8

import pickle
import pathlib
import logging
from datetime import datetime
from itertools import count

from pandas import DataFrame

from dgp.gui.qtenum import QtItemFlags, QtDataRoles
from .meterconfig import MeterConfig, AT1Meter
from .etc import gen_uuid
from .types import DataSource, FlightLine, TreeItem
from .enums import DataTypes
from . import datamanager as dm
from .enums import DataTypes

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

_log = logging.getLogger(__name__)
DATA_DIR = 'data'


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

    def __init__(self, path: pathlib.Path, name: str, description: str=None,
                 model_parent=None):
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
        self.projectdir = pathlib.Path(path)

        if not self.projectdir.exists():
            raise FileNotFoundError

        if not self.projectdir.is_dir():
            raise NotADirectoryError

        self.name = name
        self.description = description or ''

        dm.init(self.projectdir.joinpath(DATA_DIR))

        # Store MeterConfig objects in dictionary keyed by the meter name
        self._sensors = {}

        _log.debug("Gravity Project Initialized.")

    def data(self, role: QtDataRoles):
        if role == QtDataRoles.DisplayRole:
            return self.name
        return super().data(role)

    @property
    def model(self):
        return self._model_parent

    @model.setter
    def model(self, value):
        self._model_parent = value

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
        dm.init(self.projectdir.joinpath('data'))


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
        uid = kwargs.get('uuid', gen_uuid('flt'))
        super().__init__(uid, parent=None)

        self.name = name
        self._project = project
        self._icon = ':/icons/airborne'
        self.style = {'icon': ':/icons/airborne',
                      QtDataRoles.BackgroundRole: 'LightGray'}
        self.meter = meter
        self.date = kwargs.get('date', datetime.today())

        # Flight attribute dictionary, containing survey values e.g. still
        # reading, tie location/value
        self._survey_values = {}

        self.flight_timeshift = 0

        # Issue #36 Plotting data channels
        self._default_plot_map = {'gravity': 0, 'long': 1, 'cross': 1}

        self._lines_uid = self.append_child(Container(ctype=FlightLine,
                                                      parent=self,
                                                      name='Flight Lines'))
        self._data_uid = self.append_child(Container(ctype=DataSource,
                                                     parent=self,
                                                     name='Data Files'))
        self._line_sequence = count()
        self.has_gravity = False
        self.has_trajectory = False

    def data(self, role):
        if role == QtDataRoles.ToolTipRole:
            return "<{name}::{uid}>".format(name=self.name, uid=self.uid)
        if role == QtDataRoles.DisplayRole:
            return "{name} - {date}".format(name=self.name, date=self.date)
        return super().data(role)

    @property
    def lines(self):
        for line in sorted(self.get_child(self._lines_uid),
                           key=lambda x: x.start):
            yield line

    @property
    def channels(self) -> list:
        """Return data channels as list of DataChannel objects"""
        rv = []
        for source in self.get_child(self._data_uid):  # type: DataSource
            # TODO: Work on active sources later
            # if source is None or not source.active:
            rv.extend(source.get_channels())
        return rv

    def get_source(self, dtype: DataTypes) -> DataSource:
        """Get the first DataSource of type 'dtype'"""
        for source in self.get_child(self._data_uid):
            if source.dtype == dtype:
                return source

    def register_data(self, datasrc: DataSource):
        """Register a data file for use by this Flight"""
        _log.info("Flight {} registering data source: {} UID: {}".format(
            self.name, datasrc.filename, datasrc.uid))
        datasrc.flight = self
        self.get_child(self._data_uid).append_child(datasrc)

        # TODO: This check needs to be revised when considering multiple datasets per flight
        if datasrc.dtype == DataTypes.GRAVITY:
            self.has_gravity = True
        elif datasrc.dtype == DataTypes.TRAJECTORY:
            self.has_trajectory = True

        # TODO: Hold off on this - breaks plot when we change source
        # print("Setting new Dsrc to active")
        # datasrc.active = True
        # self.update()

    def remove_data(self, datasrc: DataSource) -> bool:
        # TODO: This check needs to be revised when considering multiple datasets per flight
        if datasrc.dtype == DataTypes.GRAVITY:
            self.has_gravity = False
        elif datasrc.dtype == DataTypes.TRAJECTORY:
            self.has_trajectory = False
        return self.get_child(self._data_uid).remove_child(datasrc)

    def add_line(self, line: FlightLine) -> int:
        """Add a flight line to the flight by start/stop index and sequence
        number.

        Returns
        -------
        Sequence number of added line.
        """
        lines = self.get_child(self._lines_uid)
        line.sequence = next(self._line_sequence)
        lines.append_child(line)
        return line.sequence

    def get_line(self, uid):
        return self.get_child(self._lines_uid).get_child(uid)

    def remove_line(self, uid):
        """ Remove a flight line """
        lines = self.get_child(self._lines_uid)
        child = lines.get_child(uid)
        lines.remove_child(child)

    def clear_lines(self):
        """Removes all Lines from Flight"""
        raise NotImplementedError("clear_lines not implemented yet.")

    def __iter__(self):
        """
        Implement class iteration, allowing iteration through FlightLines
        Yields
        -------
        FlightLine : NamedTuple
            Next FlightLine in Flight.lines
        """
        for line in self.get_child(self._lines_uid):
            yield line

    def __len__(self):
        return len(self.get_child(self._lines_uid))

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
        self._gravdata = None
        self._gpsdata = None


class Container(TreeItem):
    # Arbitrary list of permitted types
    ctypes = {Flight, MeterConfig, FlightLine, DataSource}

    def __init__(self, ctype, parent=None, **kwargs):
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
        _icon = ':/icons/folder_open.png'
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
        return str(self._children)

    def __repr__(self):
        return '<Container of {} uid: {}>'.format(self.ctype, self.uid)


class AirborneProject(GravityProject):
    """
    A subclass of the base GravityProject, AirborneProject will define an
    Airborne survey project with parameters unique to airborne operations,
    and defining flight lines etc.

    """

    def __iter__(self):
        pass

    def __init__(self, path: pathlib.Path, name, description=None, parent=None):
        super().__init__(path, name, description)

        self._flight_uid = self.append_child(Container(ctype=Flight,
                                                       name="Flights",
                                                       parent=self))
        self._meter_uid = self.append_child(Container(ctype=MeterConfig,
                                                      name="Meter Configs",
                                                      parent=self))

        _log.debug("Airborne project initialized")

    def data(self, role: QtDataRoles):
        if role == QtDataRoles.DisplayRole:
            return "{} :: <{}>".format(self.name, self.projectdir.resolve())
        return super().data(role)

    def update(self, **kwargs):
        """Used to update the wrapping (parent) ProjectModel of this project for
         GUI display"""
        if self.model is not None:
            self.model.update(**kwargs)

    def add_flight(self, flight: Flight) -> None:
        flight.parent = self
        self.get_child(self._flight_uid).append_child(flight)

    def remove_flight(self, flight: Flight):
        self.get_child(self._flight_uid).remove_child(flight)

    def get_flight(self, uid):
        return self.get_child(self._flight_uid).get_child(uid)

    @property
    def count_flights(self):
        return len(self.get_child(self._flight_uid))

    @property
    def flights(self):
        for flight in self.get_child(self._flight_uid):
            yield flight
