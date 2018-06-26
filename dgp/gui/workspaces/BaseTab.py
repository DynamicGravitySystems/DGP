# coding: utf-8

from PyQt5.QtWidgets import QWidget

from dgp.lib.etc import gen_uuid


class BaseTab(QWidget):
    """Base Workspace Tab Widget - Subclass to specialize function"""
    def __init__(self, label: str, flight, parent=None, **kwargs):
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
    def flight(self):
        return self._flight

    @property
    def plot(self):
        return self._plot

    @plot.setter
    def plot(self, value):
        self._plot = value

    def data_modified(self, action: str, dsrc):
        pass

    @property
    def uid(self):
        return self._uid
