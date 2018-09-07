# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Union, Generator, List, Tuple, Any, Set, Dict
from weakref import WeakKeyDictionary, WeakSet, WeakMethod, ref

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QWidget

from dgp.core.oid import OID
from dgp.core.controllers.controller_mixins import AttributeProxy
from dgp.core.types.enumerations import DataType, StateAction
from dgp.lib.exporters import Exportable

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


class AbstractController(QStandardItem, AttributeProxy, Exportable):
    """AbstractController provides a base interface for creating Controllers

    This class provides some concrete implementations for various features
    common to all controllers:
        - Encapsulation of a model (dgp.core.models) object
        - Exposure of the underlying model entities' UID
        - Observer registration (notify observers on StateAction's)
        - Clone registration (notify clones of updates to the base object)
        - Child lookup function (get_child) to find child by its UID

    The following methods must be explicitly implemented by subclasses:
        - clone()
        - menu @property

    The following methods may be optionally implemented by subclasses:
        - children @property
        - add_child()
        - remove_child()

    Parameters
    ----------
    model
        The underlying model (from dgp.core.models) entity of this controller
    project : IAirborneController, optional
        A weak-reference is stored to the project controller for direct access
        by the controller via the :prop:`project` @property
    parent : AbstractController, optional
        A strong-reference is maintained to the parent controller object,
        accessible via the :meth:`get_parent` method
    *args
        Positional arguments are supplied to the QStandardItem constructor
    *kwargs
        Keyword arguments are supplied to the QStandardItem constructor

    Notes
    -----
    When removing/deleting a controller, the delete() method should be called on
    the child, in order for it to notify any subscribers of its impending doom.

    The update method should be extended by subclasses in order to perform
    visual updates (e.g. Item text, tooltips) when an entity attribute has been
    updated (via AttributeProxy::set_attr), call the super() method to propagate
    updates to any observers automatically.

    """
    def __init__(self, model, *args, project=None, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._model = model
        self._project = ref(project) if project is not None else None
        self._parent: AbstractController = parent
        self._clones: Set[AbstractController] = WeakSet()
        self.__cloned = False
        self._observers: Dict[StateAction, Dict] = {state: WeakKeyDictionary()
                                                    for state in StateAction}

        self.setEditable(False)
        self.setText(model.name if hasattr(model, "name") else str(model))
        self.setData(model, Qt.UserRole)

    @property
    def uid(self) -> OID:
        """Return the unique Object IDentifier for the controllers' model"""
        return self._model.uid

    @property
    def entity(self):
        """Returns the underlying core/model object of this controller"""
        return self._model

    @property
    def project(self) -> 'IAirborneController':
        return self._project() if self._project is not None else None

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
    def menu(self) -> List[MenuBinding]:
        """Return a list of MenuBinding's to construct a context menu

        Must be overridden by subclasses
        """
        raise NotImplementedError

    @property
    def parent_widget(self) -> Union[QWidget, None]:
        """Returns the parent QWidget of this items' QAbstractModel"""
        try:
            return self.model().parent()
        except AttributeError:
            return None

    def get_parent(self) -> 'AbstractController':
        return self._parent

    def set_parent(self, parent: 'AbstractController'):
        self._parent = parent

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
        """Yields children of this controller

        Override this property to provide generic access to controller children

        Yields
        ------
        AbstractController
            Children of this controller

        """
        yield from ()

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
        pass

    def remove_child(self, uid: OID, confirm: bool = True) -> bool:
        """Remove a child from this controller, and notify the child of its deletion

        Parameters
        ----------
        uid : OID
            OID of the child to remove
        confirm : bool, optional
            Optionally request that the controller confirms the action before
            removing the child, default is True

        Returns
        -------
        bool
            True on successful removal of child
            False on failure (i.e. invalid uid supplied)

        """
        pass

    def get_child(self, uid: OID) -> MaybeChild:
        """Get a child of this object by matching OID

        Parameters
        ----------
        uid : :class:`~dgp.core.oid.OID`
            Unique identifier of the child to get

        Returns
        -------
        MaybeChild
            Returns the child controller object referred to by uid if it exists
            else None

        """
        for child in self.children:
            if uid == child.uid:
                return child

    def export(self, recursive=True) -> Dict[str, object]:
        raise NotImplementedError

    def __str__(self):
        return str(self.entity)

    def __hash__(self):
        return hash(self.uid)


# noinspection PyAbstractClass
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


# noinspection PyAbstractClass
class IFlightController(AbstractController):
    pass


# noinspection PyAbstractClass
class IMeterController(AbstractController):
    pass


# noinspection PyAbstractClass
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

    def get_datafile(self, group):
        raise NotImplementedError
