# coding: utf-8

from abc import ABCMeta, abstractmethod
from collections import namedtuple

from matplotlib.lines import Line2D
from pandas import Series

from dgp.lib.etc import gen_uuid

"""
Dynamic Gravity Processor (DGP) :: types.py
License: Apache License V2

Overview:
types.py is a library utility module used to define custom reusable types for 
use in other areas of the project.
"""

Location = namedtuple('Location', ['lat', 'long', 'alt'])

StillReading = namedtuple('StillReading', ['gravity', 'location', 'time'])

DataCurve = namedtuple('DataCurve', ['channel', 'data'])

DataFile = namedtuple('DataFile', ['uid', 'filename', 'fields', 'dtype'])


class AbstractTreeItem(metaclass=ABCMeta):
    """
    AbstractTreeItem provides the interface definition for an object that can
    be utilized within a heirarchial or tree model.
    This AbstractBaseClass (ABC) defines the function signatures required by
    a Tree Model implementation in QT/PyQT.
    """

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
    def child(self, uid):
        pass

    @abstractmethod
    def append_child(self, child):
        pass

    @abstractmethod
    def child_count(self):
        pass

    @abstractmethod
    def column_count(self):
        pass

    @abstractmethod
    def row(self):
        pass

    @abstractmethod
    def data(self, role=None):
        pass

    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def __len__(self):
        pass

    @abstractmethod
    def __iter__(self):
        pass


class TreeItem(AbstractTreeItem):
    """
    TreeItem provides default implementations for common model functions
    and should be used as a base class for specialized data structures that
    expect to be displayed in a QT Tree View
    """

    def __init__(self, uid, parent: AbstractTreeItem=None):

        # Private BaseClass members - should be accessed via properties
        self._parent = parent
        self._uid = uid
        self._children = []  # List is required due to need for simple ordering
        self._child_map = {}

        if parent is not None:
            parent.append_child(self)

    def __str__(self):
        return "<TreeItem(uid={})>".format(self._uid)

    def __len__(self):
        return len(self._children)

    def __iter__(self):
        for child in self._children:
            yield child

    @property
    def uid(self):
        return self._uid

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        assert isinstance(value, AbstractTreeItem)
        self._parent = value

    @property
    def children(self):
        for child in self._children:
            yield child

    def child(self, uid):
        return self._child_map.get(uid, None)

    def append_child(self, child: AbstractTreeItem):
        assert isinstance(child, AbstractTreeItem)
        if child in self._children:
            # Appending same child should have no effect
            return
        child.parent = self
        self._children.append(child)
        self._child_map[child.uid] = child

    def indexof(self, child) -> int:
        """Return the index of a child contained in this object"""
        return self._children.index(child)

    def row(self) -> int:
        """Return the row index of this TreeItem relative to its parent"""
        if self._parent is not None:
            return self._parent.indexof(self)
        return 0

    def child_count(self):
        return len(self._children)

    def column_count(self):
        return 1

    def data(self, role=None):
        raise NotImplementedError("data method must be implemented in subclass")


class PlotCurve:
    def __init__(self, uid: str, data: Series, label: str = None, axes: int = 0,
                 color: str = None):
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
