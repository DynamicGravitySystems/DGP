# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Optional, Union

from dgp.core.models.dataset import DataSet
from dgp.core.models.meter import Gravimeter
from dgp.core.oid import OID


class Flight:
    """
    Version 2 Flight Class - Designed to be de-coupled from the view implementation
    Define a Flight class used to record and associate data with an entire
    survey flight (takeoff -> landing)
    """
    __slots__ = ('uid', 'name', 'datasets', 'meter',
                 'date', 'notes', 'sequence', 'duration', '_parent')

    def __init__(self, name: str, date: Optional[datetime] = None, notes: Optional[str] = None,
                 sequence: int = 0, duration: int = 0, meter: str = None,
                 uid: Optional[OID] = None, **kwargs):
        self._parent = None
        self.uid = uid or OID(self, name)
        self.uid.set_pointer(self)
        self.name = name
        self.date = date or datetime.today()
        self.notes = notes
        self.sequence = sequence
        self.duration = duration

        self.datasets = kwargs.get('datasets', [])  # type: List[DataSet]
        self.meter: Gravimeter = meter

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return '<Flight %s :: %s>' % (self.name, self.uid)
