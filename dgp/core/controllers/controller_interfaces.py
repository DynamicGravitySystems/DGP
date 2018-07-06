# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Any, Union, Optional

from PyQt5.QtGui import QStandardItem, QStandardItemModel
from pandas import DataFrame

from dgp.core.controllers.controller_mixins import AttributeProxy
from dgp.core.oid import OID
from dgp.core.types.enumerations import DataTypes


"""
Interface module, while not exactly Pythonic, helps greatly by providing
interface definitions for the various controller modules, which often cannot 
be imported as a type hints in various modules due to circular imports.
"""


class IChild:
    def get_parent(self):
        raise NotImplementedError

    def set_parent(self, parent) -> None:
        raise NotImplementedError


class IParent:
    def add_child(self, child) -> 'IBaseController':
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

    def remove_child(self, child, row: int) -> None:
        raise NotImplementedError

    def get_child(self, uid: Union[str, OID]) -> IChild:
        raise NotImplementedError


class IBaseController(QStandardItem, AttributeProxy):
    @property
    def uid(self) -> OID:
        """Return the Object IDentifier of the underlying
        model object

        Returns
        -------
        :obj:`~dgp.core.oid.OID`
            The OID of the underlying data model object
        """
        raise NotImplementedError


class IAirborneController(IBaseController, IParent):
    def add_flight(self):
        raise NotImplementedError

    def add_gravimeter(self):
        raise NotImplementedError

    def load_file_dlg(self, datatype: DataTypes, destination: Optional['IFlightController'] = None):  # pragma: no cover
        raise NotImplementedError

    @property
    def hdf5store(self):
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

    def set_active_child(self, child, emit: bool = True):
        raise NotImplementedError

    def get_active_child(self):
        raise NotImplementedError


class IFlightController(IBaseController, IParent, IChild):
    def load_data(self, datafile) -> DataFrame:
        raise NotImplementedError

    def set_active_child(self, child, emit: bool = True):
        raise NotImplementedError

    def get_active_child(self):
        raise NotImplementedError


class IMeterController(IBaseController, IChild):
    pass
