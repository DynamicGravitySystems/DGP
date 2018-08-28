# -*- coding: utf-8 -*-
import weakref
from pathlib import Path
from typing import Union, Generator, List, Tuple, Any
from weakref import WeakKeyDictionary, WeakSet, WeakMethod, ref

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
        self._clones: Set[AbstractController] = WeakSet()
        self.__cloned = False
        self._observers: Dict[StateAction, Dict] = {state: WeakKeyDictionary()
                                                    for state in StateAction}

    @property
    def uid(self) -> OID:
        raise NotImplementedError

    def get_parent(self) -> 'AbstractController':
        return self._parent

    def set_parent(self, parent: 'AbstractController'):
        self._parent = parent

    @property
    def clones(self):
        """Yields any active (referenced) clones of this controller"""
        for clone in self._clones:
            yield clone

    def clone(self):
        """Return a clone of this controller for use in other UI models

        Must be overridden by subclasses, subclasses should call register_clone
        on the cloned instance to ensure update events are propagated to the
        clone.
        """
        raise NotImplementedError

    @property
    def is_clone(self) -> bool:
        return self.__cloned

    @is_clone.setter
    def is_clone(self, value: bool):
        self.__cloned = value

    def register_clone(self, clone: 'AbstractController'):
        clone.is_clone = True
        self._clones.add(clone)

    @property
    def is_active(self) -> bool:
        """Return True if there are any active observers of this controller"""
        return len(self._observers[StateAction.DELETE]) > 0



    @property
    def parent_widget(self) -> Union[QWidget, None]:
        try:
            return self.model().parent()
        except AttributeError:
            return None

    @property
    def menu(self) -> List[MenuBinding]:
        raise NotImplementedError
    def register_observer(self, observer, callback, state: StateAction) -> None:
        """Register an observer with this controller

        Observers will be notified when the controller undergoes the applicable
        StateAction (UPDATE/DELETE), via the supplied callback method.

        Parameters
        ----------
        observer : object
            The observer object, note must be weak reference'able, when the
            observer is deleted or gc'd any callbacks will be dropped.
        callback : bound method
            Bound method to call when the state action occurs.
            Note this must be a *bound* method of an object, builtin functions
            or PyQt signals will raise an error.
        state : StateAction
            Action to observe in the controller, currently only meaningful for
            UPDATE or DELETE

        """
        self._observers[state][observer] = WeakMethod(callback)

    def delete(self) -> None:
        """Notify any observers and clones that this controller is being deleted

        Also calls delete() on any children of this controller to cleanup after
        the parent has been deleted.
        """
        for child in self.children:
            child.delete()
        for cb in self._observers[StateAction.DELETE].values():
            cb()()
        for clone in self.clones:
            clone.delete()

    def update(self) -> None:
        """Notify any observers and clones that the controller state has updated

        """
        for cb in self._observers[StateAction.UPDATE].values():
            cb()()
        for clone in self.clones:
            clone.update()

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


class IFlightController(AbstractController):
    def get_parent(self) -> IAirborneController:
        raise NotImplementedError


class IMeterController(AbstractController):
    pass


class IDataSetController(AbstractController):
    @property
    def hdfpath(self) -> Path:
        raise NotImplementedError

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
