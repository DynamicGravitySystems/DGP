# -*- coding: utf-8 -*-
from typing import Any

from PyQt5.QtGui import QStandardItem

from dgp.core.types.enumerations import DataTypes


"""
Interface module, while not exactly Pythonic, helps greatly by providing
interface definitions for the various controller modules, which often cannot 
be imported as a type hints in various modules due to circular imports.
"""


class IBaseController(QStandardItem):
    def add_child(self, child):
        raise NotImplementedError

    def remove_child(self, child, row: int, confirm: bool = True):
        raise NotImplementedError

    def set_active_child(self, child, emit: bool = True):
        raise NotImplementedError

    def get_active_child(self):
        raise NotImplementedError


class IAirborneController(IBaseController):
    def add_flight(self):
        raise NotImplementedError

    def add_gravimeter(self):
        raise NotImplementedError

    def load_file(self, datatype: DataTypes):
        raise NotImplementedError

    def set_parent(self, parent):
        raise NotImplementedError

    @property
    def flight_model(self):
        raise NotImplementedError

    @property
    def meter_model(self):
        raise NotImplementedError


class IFlightController(IBaseController):
    def set_name(self, name: str, interactive: bool = False):
        raise NotImplementedError

    def set_attr(self, key: str, value: Any) -> None:
        raise NotImplementedError

