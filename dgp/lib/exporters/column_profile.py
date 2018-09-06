# -*- coding: utf-8 -*-
from enum import Enum, auto


class Category(Enum):
    Any = auto()
    Gravity = auto()
    Trajectory = auto()
    Transform = auto()
    Status = auto()
    User = auto()


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
    """ColumnProfile defines characteristics of columns available for export
    
    Parameters
    ----------
    identifier : str
        Column identifier name, this corresponds to the columns name in its 
        source DataFrame/Series
    category: :class:`Category`
        Category that this column belongs to e.g. Gravity or Trajectory.
        See the :class:`Category` enumeration.
    name : str, optional
        Optional friendly name for this column for display purposes
    unit : :class:`Unit`, optional
        Optional Unit type for representing values of this column
    description : str, optional
        Optional description for this column profile
    group : str, optional
        Optional sub-category classifier to group this profile within the
        specified category
    register : bool, optional
        If True (default) automatically register this column profile upon creation
    
    """
    __columns = []

    def __init__(self, identifier, category: Category, name=None,
                 unit: Unit = Unit.Scalar, description=None, group=None,
                 register=True):
        self.identifier = identifier
        self.name = name or self.identifier
        self.category = category
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

