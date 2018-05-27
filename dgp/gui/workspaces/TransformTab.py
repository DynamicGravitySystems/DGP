# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QGridLayout

from dgp.lib.types import DataSource
from . import BaseTab, Flight


class TransformTab(BaseTab):
    _name = "Transform"

    def __init__(self, label: str, flight: Flight):
        super().__init__(label, flight)
        self._layout = QGridLayout()
        self.setLayout(self._layout)

        self.fc = None
        self.plots = []
        self._nodes = {}

    def data_modified(self, action: str, dsrc: DataSource):
        """Slot: Called when a DataSource has been added/removed from the
        Flight this tab/workspace is associated with."""
        if action.lower() == 'add':
            return
        elif action.lower() == 'remove':
            return
