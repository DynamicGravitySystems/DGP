# coding: utf-8

from abc import ABC, abstractmethod
from collections import namedtuple

from matplotlib.lines import Line2D
from pandas import Series

from dgp.lib.etc import gen_uuid

"""
Dynamic Gravity Processor (DGP) :: types.py
License: Apache License V2

Overview:
types.py is a library utility module used to define custom reusable types for use in other areas of the project.
"""


Location = namedtuple('Location', ['lat', 'long', 'alt'])

StillReading = namedtuple('StillReading', ['gravity', 'location', 'time'])

DataCurve = namedtuple('DataCurve', ['channel', 'data'])

DataFile = namedtuple('DataFile', ['uid', 'filename', 'fields', 'dtype'])


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


class PlotCurve:
    def __init__(self, uid: str, data: Series, label: str=None, axes: int=0, color: str=None):
        self._uid = uid
        self._data = data
        self._label = label
        if label is None:
            self._label = self._data.name
        self.axes = axes
        self._line2d = None
        self._changed = False

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def data(self) -> Series:
        return self._data

    @data.setter
    def data(self, value: Series):
        self._changed = True
        self._data = value

    @property
    def label(self) -> str:
        return self._label

    @property
    def line2d(self):
        return self._line2d

    @line2d.setter
    def line2d(self, value: Line2D):
        assert isinstance(value, Line2D)
        print("Updating line in PlotCurve: ", self._label)
        self._line2d = value
        print(self._line2d)


class FlightLine(TreeItem):
    def __init__(self, start, stop, sequence, file_ref, uid=None, parent=None):
        if uid is None:
            self._uid = gen_uuid('ln')
        else:
            self._uid = uid
            
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
