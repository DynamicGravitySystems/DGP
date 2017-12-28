# coding: utf-8

import json
from abc import ABCMeta, abstractmethod
from collections import namedtuple
from typing import Union, Generator, List

from pandas import Series, DataFrame

from dgp.lib.etc import gen_uuid
from dgp.gui.qtenum import QtItemFlags, QtDataRoles
import dgp.lib.datamanager as dm

"""
Dynamic Gravity Processor (DGP) :: lib/types.py
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
    def data(self, role):
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
    def flags(self):
        pass

    @abstractmethod
    def update(self, **kwargs):
        pass


class BaseTreeItem(AbstractTreeItem):
    """
    Define a lightweight bare-minimum implementation of the
    AbstractTreeItem to ease futher specialization in subclasses.
    """
    def __init__(self, uid, parent: AbstractTreeItem=None):
        self._uid = uid
        self._parent = parent
        self._children = []
        # self._child_map = {}  # Used for fast lookup by UID
        if parent is not None:
            parent.append_child(self)

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
            # try:
            #     self._parent.remove_child(self)
            # except ValueError:
            #     print("Couldn't reove self from parent")
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

    def data(self, role: QtDataRoles):
        raise NotImplementedError("data(role) must be implemented in subclass.")

    def child(self, index: int) -> AbstractTreeItem:
        return self._children[index]

    def get_child(self, uid: str) -> 'BaseTreeItem':
        """Get a child by UID reference."""
        for child in self._children:
            if child.uid == uid:
                return child
        else:
            raise KeyError("Child UID does not exist.")

    def append_child(self, child: AbstractTreeItem) -> str:
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

        Returns
        -------
        str:
            UID of appended child

        Raises
        ------
        AssertionError:
            If child is not an instance of AbstractTreeItem, an Assertion
            Error is raised, and the child will not be appended to this object.
        """
        assert isinstance(child, BaseTreeItem)
        if child in self._children:
            # Appending same child should have no effect
            return child.uid
        child.parent = self
        self._children.append(child)
        self.update()
        return child.uid

    def remove_child(self, child: AbstractTreeItem):
        if child not in self._children:
            return False
        child.parent = None
        self._children.remove(child)
        self.update()
        return True

    def insert_child(self, child: AbstractTreeItem, index: int) -> bool:
        if index == -1:
            self.append_child(child)
            return True
        print("Inserting ATI child at index: ", index)
        self._children.insert(index, child)
        self.update()
        return True

    def child_count(self):
        """Return number of children belonging to this object"""
        return len(self._children)

    def column_count(self):
        """Default column count is 1, and the current models expect a single
        column Tree structure."""
        return 1

    def indexof(self, child) -> int:
        """Return the index of a child contained in this object"""
        try:
            return self._children.index(child)
        except ValueError:
            print("Invalid child passed to indexof")
            return -1

    def row(self) -> Union[int, None]:
        """Return the row index of this TreeItem relative to its parent"""
        if self._parent:
            return self._parent.indexof(self)
        return 0

    def flags(self) -> int:
        """Returns default flags for Tree Items, override this to enable
        custom behavior in the model."""
        return QtItemFlags.ItemIsSelectable | QtItemFlags.ItemIsEnabled

    def update(self, **kwargs):
        """Propogate update up to the parent that decides to catch it"""
        if self.parent is not None:
            self.parent.update(**kwargs)


_style_roles = {QtDataRoles.BackgroundRole: 'bg',
                QtDataRoles.ForegroundRole: 'fg',
                QtDataRoles.DecorationRole: 'icon',
                QtDataRoles.FontRole: 'font'}


class TreeItem(BaseTreeItem):
    """
    TreeItem extends BaseTreeItem and adds some extra convenience methods
    (__str__, __len__, __iter__, __getitem__, __contains__), as well as
    defining a default data() method which can apply styles set via the style
    property in this class.
    """

    def __init__(self, uid: str, parent: AbstractTreeItem=None):
        super().__init__(uid, parent)
        self._style = {}

    def __str__(self):
        return "<TreeItem(uid={})>".format(self.uid)

    def __len__(self):
        return self.child_count()

    def __iter__(self):
        for child in self.children:
            yield child

    def __getitem__(self, key: Union[int, str]):
        """Permit child access by ordered index, or UID"""
        if not isinstance(key, (int, str)):
            raise ValueError("Key must be int or str type")
        if isinstance(key, str):
            return self.get_child(key)
        return self.child(key)

    def __contains__(self, item: AbstractTreeItem):
        return item in self.children

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, value):
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
        if role in _style_roles:
            key = _style_roles[role]
            return self._style.get(key, None)
        return None


class ChannelListHeader(BaseTreeItem):
    """
    A simple Tree Item with a label, to be used as a header/label. This
    TreeItem accepts children.
    """
    def __init__(self, index: int=-1, ctype='Available', supports_drop=True,
                 max_children=None, parent=None):
        super().__init__(uid=gen_uuid('clh_'), parent=parent)
        self.label = '{ctype} #{index}'.format(ctype=ctype, index=index)
        self.index = index
        self._supports_drop = supports_drop
        self.max_children = max_children

    @property
    def droppable(self):
        if not self._supports_drop:
            return False
        if self.max_children is None:
            return True
        if self.child_count() >= self.max_children:
            return False
        return True

    def data(self, role: QtDataRoles):
        if role == QtDataRoles.DisplayRole:
            return self.label
        return None

    def remove_child(self, child: Union[AbstractTreeItem, str]):
        super().remove_child(child)


class FlightLine(TreeItem):
    """
    Simple TreeItem to represent a Flight Line selection, storing a start
    and stop index, as well as the reference to the data it relates to.
    This TreeItem does not accept children.
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


class DataSource(BaseTreeItem):
    """
    The DataSource object is designed to hold a reference to a given UID/File
    that has been imported and stored by the Data Manager.
    This object provides a method load() that enables the caller to retrieve
    the data pointed to by this object from the Data Manager.

    As DataSource is derived from BaseTreeItem, it supports being displayed
    in a QTreeView via an AbstractItemModel derived class.

    Attributes
    ----------
    filename : str
        Record of the canonical path of the original data file.
    fields : list(str)
        List containing names of the fields (columns) available from the
        source data.
    dtype : str
        Data type (i.e. GPS/Gravity) of the data pointed to by this object.

    """
    def __init__(self, uid, filename: str, fields: List[str], dtype: str):
        """Create a DataSource item with UID matching the managed file UID
        that it points to."""
        super().__init__(uid)
        self.filename = filename
        self.fields = fields
        self.dtype = dtype

    def get_channels(self) -> List['DataChannel']:
        """
        Create a new list of DataChannels.

        Notes
        -----
        The reason we construct a new list of new DataChannels instances is
        due the probability of the DataChannels being used in multiple
        models.

        If we returned instead a reference to previously created instances,
        we would unpredictable behavior when their state or parent is modified.

        Returns
        -------
        channels : List[DataChannel]
            List of DataChannels constructed from fields available to this
            DataSource.

        """
        return [DataChannel(field, self) for field in self.fields]

    def load(self, field=None) -> Union[Series, DataFrame]:
        """Load data from the DataManager and return the specified field."""
        data = dm.get_manager().load_data(self.uid)
        if field is not None:
            return data[field]
        return data

    def data(self, role: QtDataRoles):
        if role == QtDataRoles.DisplayRole:
            return "{dtype}: {fname}".format(dtype=self.dtype,
                                             fname=self.filename)
        if role == QtDataRoles.ToolTipRole:
            return "UID: {}".format(self.uid)

    def children(self):
        return []


class DataChannel(BaseTreeItem):
    def __init__(self, label, source: DataSource, parent=None):
        super().__init__(gen_uuid('dcn'), parent=parent)
        self.label = label
        self.field = label
        self._source = source
        self.plot_style = ''
        self.units = ''
        self._plotted = False
        self._index = -1

    @property
    def plotted(self):
        return self._plotted

    @property
    def index(self):
        if not self._plotted:
            return -1
        return self._index

    def plot(self, index: Union[int, None]) -> None:
        if index is None:
            self._plotted = False
            self._index = -1
        else:
            self._index = index
            self._plotted = True

    def series(self, force=False) -> Series:
        """Return the pandas Series referenced by this DataChannel
        Parameters
        ----------
        force : bool, optional
            Reserved for future use, force the DataManager to reload the
            Series from disk.
        """
        return self._source.load(self.field)

    def data(self, role: QtDataRoles):
        if role == QtDataRoles.DisplayRole:
            return self.label
        if role == QtDataRoles.UserRole:
            return self.field
        return None

    def flags(self):
        return super().flags() | QtItemFlags.ItemIsDragEnabled | \
               QtItemFlags.ItemIsDropEnabled

    def orphan(self):
        """Remove the current object from its parents' list of children."""
        if self.parent is None:
            return True
        try:
            parent = self.parent
            res = parent.remove_child(self)
            return res
        except ValueError:
            return False
