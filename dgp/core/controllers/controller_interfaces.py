# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Union, Generator, List, Tuple, Any

from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QWidget

from dgp.core.controllers.controller_mixins import AttributeProxy
from dgp.core.oid import OID
from dgp.core.types.enumerations import DataTypes


"""
Interface module, while not exactly Pythonic, helps greatly by providing
interface definitions for the various controller modules, which often cannot 
be imported as a type hints in various modules due to circular imports.

Abstract Base Classes (collections.ABC) are not used due to the complications
invited with multiple inheritance and metaclass mis-matching. As most controller
level classes also subclass QStandardItem and/or AttributeProxy.
"""

MenuBinding = Tuple[str, Tuple[Any, ...]]


class DGPObject:
    @property
    def uid(self) -> OID:
        """Returns the unique Object IDentifier of the object

        Returns
        -------
        :class:`~dgp.core.oid.OID`
            Unique Object Identifier of the object.

        """
        raise NotImplementedError


class IChild(DGPObject):
    """A class sub-classing IChild can be a child object of a class which is an
    :class:`IParent`.

    The IChild interface defines properties to determine if the child can be
    activated, and if it is currently activated.
    Methods are defined so that the child may retrieve or set a reference to its
    parent object.
    The set_active method is provided for the Parent object to notify the child
    of an activation state change and to update its visual state.

    """
    def get_parent(self) -> 'IParent':
        raise NotImplementedError

    def set_parent(self, parent) -> None:
        raise NotImplementedError

    @property
    def can_activate(self) -> bool:
        return False

    @property
    def is_active(self) -> bool:
        if not self.can_activate:
            return False
        raise NotImplementedError

    def set_active(self, state: bool) -> None:
        """Called to visually set the child to the active state.

        If a child needs to activate itself it should call activate_child on its
        parent object, this ensures that siblings can be deactivated if the
        child should be exclusively active.

        Parameters
        ----------
        state : bool
            Set the objects active state to the boolean state

        """
        if not self.can_activate:
            return
        raise NotImplementedError


# TODO: Rename to AbstractParent
class IParent(DGPObject):
    """A class sub-classing IParent provides the ability to add/get/remove
    :class:`IChild` objects, as well as a method to iterate through children.

    Child objects may be activated by the parent if child.can_activate is True.
    Parent objects should call set_active on children to update their internal
    active state, and to allow children to perform any necessary visual updates.

    """
    @property
    def children(self) -> Generator[IChild, None, None]:
        """Return a generator of IChild objects specific to the parent.

        Returns
        -------
        Generator[IChild, None, None]

        """
        raise NotImplementedError

    def add_child(self, child) -> 'IChild':
        """Add a child object to the controller, and its underlying
        data object.

        Parameters
        ----------
        child :
            The child data object to be added (from :mod:`dgp.core.models`)

        Returns
        -------
        :class:`IBaseController`
            A reference to the controller object wrapping the added child

        Raises
        ------
        :exc:`TypeError`
            If the child is not an allowed type for the controller.
        """
        raise NotImplementedError

    def remove_child(self, child, confirm: bool = True) -> None:
        raise NotImplementedError

    def get_child(self, uid: Union[str, OID]) -> IChild:
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

    def activate_child(self, uid: OID, exclusive: bool = True,
                       emit: bool = False) -> Union[IChild, None]:
        """Activate a child referenced by the given OID, and return a reference
        to the activated child.
        Children may be exclusively activated (default behavior), in which case
        all other children of the parent will be set to inactive.

        Parameters
        ----------
        uid : :class:`~dgp.core.oid.OID`
        exclusive : bool, Optional
            If exclusive is True, all other children will be deactivated
        emit : bool, Optional

        Returns
        -------
        :class:`IChild`
            The child object that was activated

        """
        child = self.get_child(uid)
        try:
            child.set_active(True)
            if exclusive:
                for other in [c for c in self.children if c.uid != uid]:
                    other.set_active(False)
        except AttributeError:
            return None
        else:
            return child

    @property
    def active_child(self) -> Union[IChild, None]:
        """Returns the first active child object, or None if no children are
        active.

        """
        return next((child for child in self.children if child.is_active), None)


class IBaseController(QStandardItem, AttributeProxy, DGPObject):
    @property
    def parent_widget(self) -> Union[QWidget, None]:
        try:
            return self.model().parent()
        except AttributeError:
            return None

    @property
    def menu(self) -> List[MenuBinding]:
        raise NotImplementedError


class IAirborneController(IBaseController, IParent, IChild):
    def add_flight_dlg(self):
        raise NotImplementedError

    def add_gravimeter_dlg(self):
        raise NotImplementedError

    def load_file_dlg(self, datatype: DataTypes,
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


class IFlightController(IBaseController, IParent, IChild):
    @property
    def can_activate(self):
        return True

    @property
    def project(self) -> IAirborneController:
        raise NotImplementedError

    def get_parent(self) -> IAirborneController:
        raise NotImplementedError


class IMeterController(IBaseController, IChild):
    pass


class IDataSetController(IBaseController, IChild):
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
