# -*- coding: utf-8 -*-
from enum import Enum
from typing import List


class Group(Enum):
    Gravity = 'gravity'
    Trajectory = 'trajectory'
    AirborneTransform = 'airborne_transform'


class Unit(Enum):
    Scalar = ""
    Gal = "Gal"
    mGal = "mGal"
    DegC = "°C"
    DegF = "°F"
    Degrees = "°"
    inchHg = "inHg"
    Meters = "m"


class ColumnProfile:
    __columns = []

    def __init__(self, name, group: Group, identifier=None,
                 unit: Unit=Unit.Scalar, description="", register=True):
        self.name = name
        self.group = group
        self.identifier = identifier or name
        self.unit = unit
        self.description = description

        if register:
            self.register(self)

    @property
    def display_unit(self) -> str:
        return self.unit.name

    @classmethod
    def columns(cls) -> List['ColumnProfile']:
        return cls.__columns[:]

    @classmethod
    def register(cls, instance):
        cls.__columns.append(instance)

    @classmethod
    def from_identifier(cls, identifier: str):
        for col in cls.columns():
            if col.identifier == identifier:
                return col


gravity = ColumnProfile("gravity", Group.Gravity, unit=Unit.mGal)
long_acc = ColumnProfile("Long Axis Acceleration", Group.Gravity, "long_accel",
                         unit=Unit.Gal)
cross_acc = ColumnProfile("Cross Axis Acceleration", Group.Gravity,
                          "cross_accel", unit=Unit.Gal)
beam = ColumnProfile("beam", Group.Gravity, unit=Unit.Gal)
s_temp = ColumnProfile("Sensor Temperature", Group.Gravity, "temp",
                       unit=Unit.DegC)
pressure = ColumnProfile("Sensor Pressure", Group.Gravity, "pressure",
                         unit=Unit.inchHg)
e_temp = ColumnProfile("Electronics Temperature", Group.Gravity, "Etemp",
                       unit=Unit.DegC)

latitude = ColumnProfile("latitude", Group.Trajectory, unit=Unit.Degrees)
longitude = ColumnProfile("longitude", Group.Trajectory, unit=Unit.Degrees)
gps_week = ColumnProfile("GPS Week", Group.Trajectory, "gps_week")
gps_sow = ColumnProfile("GPS Seconds of Week", Group.Trajectory, "gps_sow")
