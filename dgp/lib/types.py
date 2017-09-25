# coding: utf-8

from abc import ABC, abstractmethod
from collections import namedtuple

from dgp.lib.etc import gen_uuid

"""
Dynamic Gravity Processor (DGP) :: types.py
License: Apache License V2

Overview:
types.py is a library utility module used to define custom reusable types for use in other areas of the project.
"""


Location = namedtuple('Location', ['lat', 'long', 'alt'])

StillReading = namedtuple('StillReading', ['gravity', 'location', 'time'])

# FlightLine = namedtuple('FlightLine', ['uid', 'sequence', 'file_ref', 'start', 'end', 'parent'])

DataCurve = namedtuple('DataCurve', ['channel', 'data'])

# DataPacket = namedtuple('DataPacket', ['data', 'path', 'dtype'])


class TreeItem(ABC):
    """Abstract Base Class for an object that can be displayed in a hierarchical 'tree' view."""
    @property
    @abstractmethod
    def uid(self):
        pass

    @property
    @abstractmethod
    def parent(self):
        pass

    @parent.setter
    @abstractmethod
    def parent(self, value):
        pass

    @property
    @abstractmethod
    def children(self):
        pass

    @abstractmethod
    def data(self, role=None):
        pass

    @abstractmethod
    def __str__(self):
        pass


class FlightLine(TreeItem):
    def __init__(self, start, stop, sequence, file_ref, parent=None):
        self._uid = gen_uuid('ln')
        self.start = start
        self.stop = stop
        self._file = file_ref  # UUID of source file for this line
        self._sequence = sequence
        self._parent = parent

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value

    def data(self, role=None):
        if role == 1:  # DecorationRole (Icon)
            return None
        return str(self)

    @property
    def uid(self):
        return self._uid

    @property
    def children(self):
        return []

    def __str__(self):
        return 'Line({start},{stop})'.format(start=self.start, stop=self.stop)

