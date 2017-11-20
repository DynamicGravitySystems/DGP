# coding: utf-8

from datetime import datetime
from abc import ABCMeta, abstractmethod
from collections import namedtuple
from typing import Union, Generator

from matplotlib.lines import Line2D
from pandas import Series

from dgp.lib.etc import gen_uuid
from dgp.gui.qtenum import QtItemFlags, QtDataRoles

"""
Dynamic Gravity Processor (DGP) :: types.py
License: Apache License V2

Overview:
types.py is a library utility module used to define custom reusable types for 
use in other areas of the project.

The TreeItem and AbstractTreeItem classes are designed to be subclassed by 
items for display in a QTreeView widget. The classes themselves are Qt 
agnostic, meaning they can be safely pickled, and there is no dependence on 
any Qt modules.
"""

Location = namedtuple('Location', ['lat', 'long', 'alt'])

StillReading = namedtuple('StillReading', ['gravity', 'location', 'time'])

DataCurve = namedtuple('DataCurve', ['channel', 'data'])

# DataFile = namedtuple('DataFile', ['uid', 'filename', 'fields', 'dtype'])


class AbstractTreeItem(metaclass=ABCMeta):
    """
    AbstractTreeItem provides the interface definition for an object that can
    be utilized within a heirarchial or tree model.
    This AbstractBaseClass (ABC) defines the function signatures required by
    a Tree Model implementation in QT/PyQT.
    AbstractTreeItem is also utilized to enforce some level of type safety by
    providing model consumers a simple way to perform type checking on
    instances inherited from this class.
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
    def child(self, index):
        pass

    @abstractmethod
    def append_child(self, child):
        pass

    @abstractmethod
    def remove_child(self, child):
        pass

    @abstractmethod
    def child_count(self):
        pass

    @abstractmethod
    def column_count(self):
        pass

    @abstractmethod
    def indexof(self, child):
        pass

    @abstractmethod
    def row(self):
        pass

    @abstractmethod
    def data(self, role):
        pass

    @abstractmethod
    def flags(self):
        pass

    @abstractmethod
    def update(self, **kwargs):
        pass


class TreeItem(AbstractTreeItem):
    """
    TreeItem provides default implementations for common model functions
    and should be used as a base class for specialized data structures that
    expect to be displayed in a QT Tree View.
    """

    def __init__(self, uid: str, parent: AbstractTreeItem=None):

        # Private BaseClass members - should be accessed via properties
        self._parent = parent
        self._uid = uid
        self._children = []  # List is required due to need for ordering
        self._child_map = {}  # Used for fast lookup by UID
        self._style = {}
        self._style_roles = {QtDataRoles.BackgroundRole: 'bg',
                             QtDataRoles.ForegroundRole: 'fg',
                             QtDataRoles.DecorationRole: 'icon',
                             QtDataRoles.FontRole: 'font'}

        if parent is not None:
            parent.append_child(self)

    def __str__(self):
        return "<TreeItem(uid={})>".format(self._uid)

    def __len__(self):
        return len(self._children)

    def __iter__(self):
        for child in self._children:
            yield child

    def __getitem__(self, key: Union[int, str]):
        """Permit child access by ordered index, or UID"""
        if not isinstance(key, (int, str)):
            raise ValueError("Key must be int or str type")
        if type(key) is int:
            return self._children[key]

        if type(key) is str:
            return self._child_map[key]

    def __contains__(self, item: AbstractTreeItem):
        return item in self._children

    @property
    def uid(self) -> str:
        """Returns the unique identifier of this object."""
        return self._uid

    @property
    def parent(self) -> Union[AbstractTreeItem, None]:
        """Returns the parent of this object."""
        return self._parent

    @parent.setter
    def parent(self, value: AbstractTreeItem):
        """Sets the parent of this object."""
        if value is None:
            self._parent = None
            return
        assert isinstance(value, AbstractTreeItem)
        self._parent = value
        self.update()

    @property
    def children(self) -> Generator[AbstractTreeItem, None, None]:
        """Generator property, yields children of this object."""
        for child in self._children:
            yield child

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, value: dict):
        # TODO: Check for valid style params
        self._style = value

    def data(self, role: QtDataRoles):
        """
        Return contextual data based on supplied role.
        If a role is not defined or handled by descendents they should return
        None, and the model should be take this into account.
        TreeType provides a basic default implementation, which will also
        handle common style parameters. Descendant classes should provide
        their own definition to override specific roles, and then call the
        base data() implementation to handle style application. e.g.
        >>> def data(self, role: QtDataRoles):
        >>>     if role == QtDataRoles.DisplayRole:
        >>>         return "Custom Display: " + self.name
        >>>     # Allow base class to apply styles if role not caught above
        >>>     return super().data(role)
        """
        if role == QtDataRoles.DisplayRole:
            return str(self)
        if role == QtDataRoles.ToolTipRole:
            return self.uid
        # Allow style specification by QtDataRole or by name e.g. 'bg', 'fg'
        if role in self._style:
            return self._style[role]
        if role in self._style_roles:
            key = self._style_roles[role]
            return self._style.get(key, None)
        return None

    def child(self, index: Union[int, str]):
        if isinstance(index, str):
            return self._child_map[index]
        return self._children[index]

    def append_child(self, child: AbstractTreeItem) -> None:
        """
        Appends a child AbstractTreeItem to this object. An object that is
        not an instance of AbstractTreeItem will be rejected and an Assertion
        Error will be raised.
        Likewise if a child already exists within this object, it will
        silently continue without duplicating the child.
        Parameters
        ----------
        child: AbstractTreeItem
            Child AbstractTreeItem to append to this object.

        Raises
        ------
        AssertionError:
            If child is not an instance of AbstractTreeItem, an Assertion
            Error is raised, and the child will not be appended to this object.
        """
        assert isinstance(child, AbstractTreeItem)
        if child in self._children:
            # Appending same child should have no effect
            return
        child.parent = self
        self._children.append(child)
        self._child_map[child.uid] = child
        self.update()

    def remove_child(self, child: Union[AbstractTreeItem, str]):
        # Allow children to be removed by UID
        if isinstance(child, str):
            child = self._child_map[child]

        if child not in self._children:
            raise ValueError("Child does not exist for this parent")
        # child.parent = None
        del self._child_map[child.uid]
        self._children.remove(child)
        self.update()

    def indexof(self, child) -> Union[int, None]:
        """Return the index of a child contained in this object"""
        try:
            return self._children.index(child)
        except ValueError:
            print("Invalid child passed to indexof")
            return None

    def row(self) -> Union[int, None]:
        """Return the row index of this TreeItem relative to its parent"""
        if self._parent:
            return self._parent.indexof(self)
        return 0

    def child_count(self):
        """Return number of children belonging to this object"""
        return len(self._children)

    def column_count(self):
        """Default column count is 1, and the current models expect a single
        column Tree structure."""
        return 1

    def flags(self) -> int:
        """Returns default flags for Tree Items, override this to enable
        custom behavior in the model."""
        return QtItemFlags.ItemIsSelectable | QtItemFlags.ItemIsEnabled

    def update(self, **kwargs):
        """Propogate update up to the parent that decides to catch it"""
        if self.parent is not None:
            self.parent.update(**kwargs)


class PlotCurve:
    def __init__(self, uid: str, data: Series, label: str=None, axes: int=0,
                 color: str=None):
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
    """
    Simple TreeItem to represent a Flight Line selection, storing a start
    and stop index, as well as the reference to the data it relates to.
    This TreeItem does not permit the addition of children.
    """
    def __init__(self, start, stop, sequence, file_ref, uid=None, parent=None):
        super().__init__(uid, parent)

        self._start = start
        self._stop = stop
        self._file = file_ref  # UUID of source file for this line
        self._sequence = sequence
        self._label = None

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        self._label = value
        self.update()

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, value):
        self._start = value
        self.update()

    @property
    def stop(self):
        return self._stop

    @stop.setter
    def stop(self, value):
        self._stop = value
        self.update()

    def data(self, role):
        if role == QtDataRoles.DisplayRole:
            if self.label:
                return "Line {lbl} {start} :: {end}".format(lbl=self.label,
                                                            start=self.start,
                                                            end=self.stop)
            return str(self)
        if role == QtDataRoles.ToolTipRole:
            return "Line UID: " + self.uid
        return super().data(role)

    def append_child(self, child: AbstractTreeItem):
        """Override base to disallow adding of children."""
        raise ValueError("FlightLine does not accept children.")

    def __str__(self):
        if self.label:
            name = self.label
        else:
            name = 'Line'
        return '{name} {start:%H:%M:%S} -> {stop:%H:%M:%S}'.format(
            name=name, start=self.start, stop=self.stop)


class DataFile(TreeItem):
    def __init__(self, uid, filename, fields, dtype):
        super().__init__(uid)
        self.filename = filename
        self.fields = fields
        self.dtype = dtype

    def data(self, role: QtDataRoles):
        if role == QtDataRoles.DisplayRole:
            return "{dtype}: {fname}".format(dtype=self.dtype,
                                             fname=self.filename)
        super().data(role)

