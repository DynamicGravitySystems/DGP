# -*- coding: utf-8 -*-
import logging
from typing import Union, Generator, cast

from PyQt5.QtGui import QStandardItemModel

from . import controller_helpers as helpers
from dgp.core.oid import OID
from dgp.core.controllers.dataset_controller import DataSetController
from dgp.core.controllers.controller_interfaces import IAirborneController, IFlightController
from dgp.core.models.dataset import DataSet
from dgp.core.models.flight import Flight
from dgp.core.types.enumerations import DataType, Icon
from dgp.gui.dialogs.add_flight_dialog import AddFlightDialog


class FlightController(IFlightController):
    """
    FlightController is a wrapper around :obj:`Flight` objects, and provides
    a presentation and interaction layer for use of the underlying Flight
    instance.
    All user-space mutations or queries to a Flight object should be proxied
    through a FlightController in order to ensure that the data and presentation
    state is kept synchronized.

    As a subclass of :obj:`QStandardItem` the FlightController can be directly
    added as a child to another QStandardItem, or as a row/child in a
    :obj:`QAbstractItemModel` or :obj:`QStandardItemModel`
    The default display behavior is to provide the Flights Name.
    A :obj:`QIcon` or string path to a resource can be provided for decoration.

    FlightController implements the AttributeProxy mixin (via AbstractController),
    which allows access to the underlying :class:`Flight` attributes via the
    get_attr and set_attr methods.

    Parameters
    ----------
    flight : :class:`Flight`
        The underlying Flight model object to wrap with this controller
    project : :class:`IAirborneController`
        The parent (owning) project for this flight controller

    """

    def __init__(self, flight: Flight, project: IAirborneController):
        """Assemble the view/controller repr from the base flight object."""
        super().__init__(model=flight, project=project, parent=project)
        self.log = logging.getLogger(__name__)
        self.setIcon(Icon.AIRBORNE.icon())

        self._dataset_model = QStandardItemModel()

        for dataset in self.entity.datasets:
            control = DataSetController(dataset, project, self)
            self.appendRow(control)
            self._dataset_model.appendRow(control.clone())

        # Add a default DataSet if none defined
        if not len(self.entity.datasets):
            self.add_child(DataSet(name='DataSet-0'))

        # TODO: Consider adding MenuPrototype class which could provide the means to build QMenu
        self._bindings = [  # pragma: no cover
            ('addAction', ('Add Dataset', self._add_dataset)),
            ('addAction', ('Open Flight Tab', lambda: self.model().item_activated(self.index()))),
            ('addAction', ('Import Gravity',
                           lambda: self._load_file_dialog(DataType.GRAVITY))),
            ('addAction', ('Import Trajectory',
                           lambda: self._load_file_dialog(DataType.TRAJECTORY))),
            ('addSeparator', ()),
            ('addAction', (f'Delete {self.entity.name}', self._action_delete_self)),
            ('addAction', ('Rename Flight', self._set_name)),
            ('addAction', ('Properties', self._show_properties_dlg))
        ]
        self.update()

    @property
    def entity(self) -> Flight:
        return cast(Flight, super().entity)

    @property
    def children(self) -> Generator[DataSetController, None, None]:
        for i in range(self.rowCount()):
            yield self.child(i, 0)

    @property
    def menu(self):  # pragma: no cover
        return self._bindings

    @property
    def datasets(self) -> QStandardItemModel:
        return self._dataset_model

    def update(self):
        self.setText(self.entity.name)
        self.setToolTip(str(self.entity.uid))
        super().update()

    def clone(self):
        clone = FlightController(self.entity, self.project)
        self.register_clone(clone)
        return clone

    def add_child(self, child: DataSet) -> DataSetController:
        """Adds a child to the underlying Flight, and to the model representation
        for the appropriate child type.

        Parameters
        ----------
        child : :obj:`DataSet`
            The child model instance - either a FlightLine or DataFile

        Returns
        -------
        :obj:`DataSetController`
            Returns a reference to the controller encapsulating the added child

        Raises
        ------
        :exc:`TypeError`
            if child is not a :obj:`DataSet`

        """
        if not isinstance(child, DataSet):
            raise TypeError(f'Invalid child of type {type(child)} supplied to'
                            f'FlightController, must be {type(DataSet)}')

        self.entity.datasets.append(child)
        control = DataSetController(child, self.project, self)
        self.appendRow(control)
        self._dataset_model.appendRow(control.clone())
        self.update()
        return control

    def remove_child(self, uid: OID, confirm: bool = True) -> bool:
        """
        Remove the specified child primitive from the underlying
        :obj:`~dgp.core.models.flight.Flight` and from the respective model
        representation within the FlightController

        Parameters
        ----------
        uid : :obj:`OID`
            The child model object to be removed
        confirm : bool, optional
            If True spawn a confirmation dialog requiring user confirmation

        Returns
        -------
        bool
            True if successful
            False if user does not confirm removal action

        Raises
        ------
        :exc:`TypeError`
            if child is not a :obj:`FlightLine` or :obj:`DataFile`

        """
        child = self.get_child(uid)
        if child is None:
            raise KeyError(f'Child with uid {uid!s} not in flight {self!s}')
        if confirm:  # pragma: no cover
            if not helpers.confirm_action("Confirm Deletion",
                                          f'Are you sure you want to delete {child!r}',
                                          self.parent_widget):
                return False

        child.delete()
        self.entity.datasets.remove(child.entity)
        self._dataset_model.removeRow(child.row())
        self.removeRow(child.row())
        self.update()
        return True

    def get_child(self, uid: Union[OID, str]) -> DataSetController:
        return super().get_child(uid)

    # Menu Action Handlers
    def _activate_self(self):
        self.get_parent().activate_child(self.uid, emit=True)

    def _add_dataset(self):
        self.add_child(DataSet(name=f'DataSet-{self.datasets.rowCount()}'))

    def _action_delete_self(self, confirm: bool = True):
        self.get_parent().remove_child(self.uid, confirm)

    def _set_name(self):  # pragma: no cover
        name = helpers.get_input("Set Name", "Enter a new name:",
                                 self.get_attr('name'),
                                 parent=self.parent_widget)
        if name:
            self.set_attr('name', name)

    def _load_file_dialog(self, datatype: DataType):  # pragma: no cover
        self.get_parent().load_file_dlg(datatype, flight=self)

    def _show_properties_dlg(self):  # pragma: no cover
        AddFlightDialog.from_existing(self, self.get_parent(),
                                      parent=self.parent_widget).exec_()
