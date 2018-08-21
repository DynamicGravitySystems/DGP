# -*- coding: utf-8 -*-
import weakref
from pathlib import Path
from typing import Union, Generator, List, Tuple, Any

from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QWidget

from dgp.core.controllers.controller_mixins import AttributeProxy
from dgp.core.oid import OID
from dgp.core.types.enumerations import DataType


"""
Interface module, while not exactly Pythonic, helps greatly by providing
interface definitions for the various controller modules, which often cannot 
be imported as a type hints in various modules due to circular imports.

Abstract Base Classes (collections.ABC) are not used due to the complications
invited with multiple inheritance and metaclass mis-matching. As most controller
level classes also subclass QStandardItem and/or AttributeProxy.
"""

MenuBinding = Tuple[str, Tuple[Any, ...]]
MaybeChild = Union['AbstractController', None]


class AbstractController(QStandardItem, AttributeProxy):
    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._parent: AbstractController = parent
        self._referrers = weakref.WeakSet()
        self._update_refs = weakref.WeakKeyDictionary()
        self._delete_refs = weakref.WeakKeyDictionary()

    @property
    def uid(self) -> OID:
        raise NotImplementedError

    def get_parent(self) -> 'AbstractController':
        return self._parent

    def set_parent(self, parent: 'AbstractController'):
        self._parent = parent

    def take_reference(self, owner, on_delete=None, on_update=None) -> weakref.ReferenceType:
        """take_reference returns a weak reference to this controller

        on_delete and on_update parameters allow caller to be notified when the
        object has been deleted or updated

        Parameters
        ----------
        owner : object
        on_delete : method
        on_update : method

        Returns
        -------
        weakref.ReferenceType

        """
        if on_delete is not None:
            self._delete_refs[owner] = on_delete
        if on_update is not None:
            self._update_refs[owner] = on_update
        self._referrers.add(owner)

        return weakref.ref(self)

    @property
    def is_active(self) -> bool:
        return len(self._referrers) > 0

    def delete(self):
        """Call this when deleting a controller to allow it to clean up any open
        references (widgets)
        """
        for destruct in self._delete_refs.values():
            destruct()

    def update(self):
        for ref in self._update_refs.values():
            ref()

    @property
    def parent_widget(self) -> Union[QWidget, None]:
        try:
            return self.model().parent()
        except AttributeError:
            return None

    @property
    def menu(self) -> List[MenuBinding]:
        raise NotImplementedError

    @property
    def children(self) -> Generator['AbstractController', None, None]:
        """Return a generator of IChild objects specific to the parent.

        Returns
        -------
        Generator[AbstractController, None, None]

        """
        raise NotImplementedError

    def add_child(self, child) -> 'AbstractController':
        """Add a child object to the controller, and its underlying
        data object.

        Parameters
        ----------
        child :
            The child data object to be added (from :mod:`dgp.core.models`)

        Returns
        -------
        :class:`AbstractController`
            A reference to the controller object wrapping the added child

        Raises
        ------
        :exc:`TypeError`
            If the child is not an allowed type for the controller.
        """
        if self.children is None:
            raise TypeError(f"{self.__class__} does not support children")
        raise NotImplementedError

    def remove_child(self, child, confirm: bool = True) -> bool:
        if self.children is None:
            return False
        raise NotImplementedError

    def get_child(self, uid: Union[str, OID]) -> MaybeChild:
        """Get a child of this object by matching OID

        Parameters
        ----------
        uid : :class:`~dgp.core.oid.OID`
            Unique identifier of the child to get

        Returns
        -------
        IChild or None
            Returns the child object referred to by uid if it exists
            else None

        """
        for child in self.children:
            if uid == child.uid:
                return child

    @property
    def datamodel(self) -> object:
        raise NotImplementedError


class IAirborneController(AbstractController):
    def add_flight_dlg(self):
        raise NotImplementedError

    def add_gravimeter_dlg(self):
        raise NotImplementedError

    def load_file_dlg(self, datatype: DataType,
                      flight: 'IFlightController' = None,
                      dataset: 'IDataSetController' = None):  # pragma: no cover
        raise NotImplementedError

    @property
    def hdfpath(self) -> Path:
        raise NotImplementedError

    @property
    def path(self) -> Path:
        raise NotImplementedError

    @property
    def flight_model(self) -> QStandardItemModel:
        raise NotImplementedError

    @property
    def meter_model(self) -> QStandardItemModel:
        raise NotImplementedError

    @property
    def can_activate(self):
        return True


class IFlightController(AbstractController):
    @property
    def can_activate(self):
        return True

    def get_parent(self) -> IAirborneController:
        raise NotImplementedError


class IMeterController(AbstractController):
    pass


class IDataSetController(AbstractController):
    @property
    def hdfpath(self) -> Path:
        raise NotImplementedError

    @property
    def can_activate(self):
        return True

    def add_datafile(self, datafile) -> None:
        """
        Add a :obj:`DataFile` to the :obj:`DataSetController`, potentially
        overwriting an existing file of the same group (gravity/trajectory)

        Parameters
        ----------
        datafile : :obj:`DataFile`

        """
        raise NotImplementedError

    def add_segment(self, uid: OID, start: float, stop: float,
                    label: str = ""):
        raise NotImplementedError

    def get_segment(self, uid: OID):
        raise NotImplementedError

    def remove_segment(self, uid: OID) -> None:
        """
        Removes the specified data-segment from the DataSet.

        Parameters
        ----------
        uid : :obj:`OID`
            uid (OID or str) of the segment to be removed

        Raises
        ------
        :exc:`KeyError` if supplied uid is not contained within the DataSet

        """
        raise NotImplementedError
