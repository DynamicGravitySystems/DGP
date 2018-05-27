# coding: utf-8

from PyQt5.QtWidgets import QWidget

import dgp.lib.types as types
from dgp.lib.project import Flight
from dgp.lib.etc import gen_uuid


class BaseTab(QWidget):
    """Base Workspace Tab Widget - Subclass to specialize function"""
    def __init__(self, label: str, flight: Flight, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.label = label
        self._flight = flight
        self._uid = gen_uuid('ww')
        self._plot = None
        self._model = None

    def widget(self):
        return None

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, value):
        self._model = value

    @property
    def flight(self) -> Flight:
        return self._flight

    @property
    def plot(self):
        return self._plot

    @plot.setter
    def plot(self, value):
        self._plot = value

    def data_modified(self, action: str, dsrc: types.DataSource):
        pass

    @property
    def uid(self):
        return self._uid
