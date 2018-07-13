# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Any, Union, Optional

from PyQt5.QtGui import QStandardItem, QStandardItemModel

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

    def remove_child(self, child, confirm: bool = True) -> None:
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

    def load_file_dlg(self, datatype: DataTypes,
                      flight: 'IFlightController' = None,
                      dataset: 'IDataSetController' = None):  # pragma: no cover
        raise NotImplementedError

    @property
    def hdf5path(self) -> Path:
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
    def set_active_child(self, child, emit: bool = True):
        raise NotImplementedError

    def get_active_dataset(self):
        raise NotImplementedError

    @property
    def project(self) -> IAirborneController:
        raise NotImplementedError


class IMeterController(IBaseController, IChild):
    pass


class IDataSetController(IBaseController, IChild):
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
