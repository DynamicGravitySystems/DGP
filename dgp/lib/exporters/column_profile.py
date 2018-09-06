# -*- coding: utf-8 -*-
from enum import Enum


class Category(Enum):
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

    """ColumnProfile defines characteristics of columns available for export
    
    Parameters
    ----------
    identifier : str
        Column identifier name, this corresponds to the columns name in its 
        source DataFrame/Series
    group : :class:`Category`
        Category/category that this column belongs to e.g. Gravity or Trajectory
    name : str, optional
        Optional friendly name for this column for display purposes
    unit : :class:`Unit`, optional
        Optional Unit type for representing values of this column
    description : str, optional
        Optional description for this column profile
    register : bool, optional
        If True (default) automatically register this column profile upon creation
    
    
    """
    def __init__(self, identifier, group: Category, name=None,
                 unit: Unit = Unit.Scalar, description=None, register=True):
        self.identifier = identifier
        self.name = name or self.identifier
        self.group = group
        self.unit = unit
        self.description = description or ""

        if register:
            self.register(self)

    @property
    def display_unit(self) -> str:
        return self.unit.name

    @classmethod
    def columns(cls):
        yield from cls.__columns[:]

    @classmethod
    def register(cls, instance):
        if instance.name in [x.name for x in cls.__columns]:
            raise ValueError(f"Error registering ColumnProfile, column already "
                             f"exists with name <{instance.name}>")
        cls.__columns.append(instance)

    @classmethod
    def from_identifier(cls, identifier: str):
        for col in cls.columns():
            if col.identifier == identifier:
                return col

