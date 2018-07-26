# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Optional, Union

from dgp.core.types.reference import Reference
from dgp.core.models.dataset import DataSet
from dgp.core.models.meter import Gravimeter
from dgp.core.oid import OID


class Flight:
    """
    Flight base model (Airborne Project)

    The Flight is one of the central components of an Airborne Gravity Project,
    representing a single gravity survey flight (takeoff -> landing).
    The :class:`Flight` contains meta-data common to the overall flight
    date flown, duration, notes, etc.

    The Flight is also the parent container for 1 or more :class:`DataSet`s
    which group the Trajectory and Gravity data collected during a flight, and
    can define segments of data (flight lines), based on the flight path.

    Parameters
    ----------
    name : str
        Flight name/human-readable reference
    date : :class:`datetime`, optional
        Optional, specify the date the flight was flown, if not specified,
        today's date is used.
    notes : str, optional
        Optional, add/specify flight specific notes
    sequence : int, optional
        Optional, specify flight sequence within context of an airborne campaign
    duration : int, optional
        Optional, specify duration of the flight in hours
    meter : str, Optional
        Not yet implemented - associate a meter with this flight
        May be deprecated in favor of associating a Gravimeter with DataSets
        within the flight.

    """
    __slots__ = ('uid', 'name', 'datasets', 'date', 'notes', 'sequence',
                 'duration', '_parent')

    def __init__(self, name: str, date: Optional[datetime] = None, notes: Optional[str] = None,
                 sequence: int = 0, duration: int = 0,
                 uid: Optional[OID] = None, **kwargs):
        self._parent = Reference(self, 'parent')
        self.uid = uid or OID(self, name)
        self.uid.set_pointer(self)
        self.name = name
        self.date = date or datetime.today()
        self.notes = notes
        self.sequence = sequence
        self.duration = duration

        self.datasets = kwargs.get('datasets', [])  # type: List[DataSet]

    @property
    def parent(self):
        return self._parent.dereference()

    @parent.setter
    def parent(self, value):
        self._parent.ref = value

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'<Flight {self.name} :: {self.uid!s}>'
