# coding: utf-8

import os

from .meterconfig import MeterConfig, AT1Meter
from dgp.lib.types import location, stillreading

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
        if os.path.exists(path):
            self.dir = path
        else:
            self.dir = None
        self.name = name
        self.description = description
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

    def __str__(self):
        description = """
Gravity Project: {name}
Meters assigned: {meters}
Data Sources: {sources}""".format(name=self.name, meters=self.sensors, sources=self.data_sources)
        return description


class Flight:
    def __init__(self, flight_id: int, meter: MeterConfig):
        self.id = flight_id
        self.meter = meter

        # Known Absolute Site Reading/Location
        self.tie_value = None
        self.tie_location = None

        self.pre_still_reading = None
        self.post_still_reading = None

        self.flight_timeshift = 0

        # Flight lines should be keyed by sequence number with the value being a tuple of (start, stop) data indicies
        self.lines = {}

    def set_gravity_tie(self, gravity: float, loc: location):
        self.tie_value = gravity
        self.tie_location = loc

    def pre_still_reading(self, gravity: float, loc: location, time: float):
        self.pre_still_reading = stillreading(gravity, loc, time)

    def post_still_reading(self, gravity: float, loc: location, time: float):
        self.post_still_reading = stillreading(gravity, loc, time)

    def add_line(self, seq: int, start: float, stop: float):
        """Add a flight line to the flight by start/stop index and sequence number"""
        self.lines[seq] = (start, stop)


class AirborneProject(GravityProject):
    """
    A subclass of the base GravityProject, AirborneProject will define an Airborne survey
    project with parameters unique to airborne operations, and defining flight lines etc.
    """
    def __init__(self, path, name):
        super().__init__(path, name)
        self.flights = {}

    def add_flight(self, flight: Flight):
        self.flights[flight.id] = flight
