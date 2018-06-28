# -*- coding: utf-8 -*-

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QComboBox

from core.controllers.flight_controller import FlightController
from dgp.lib.transform.transform_graphs import SyncGravity, AirbornePost, TransformGraph
from dgp.gui.plotting.plotters import TransformPlot
from . import BaseTab
from ..ui.transform_tab_widget import Ui_TransformInterface


class TransformWidget(QWidget, Ui_TransformInterface):
    def __init__(self, flight: FlightController):
        super().__init__()
        self.setupUi(self)
        self.log = logging.getLogger(__name__)
        self._flight = flight
        self._plot = TransformPlot(rows=1)
        self._current_dataset = None

        # Initialize Models for ComboBoxes
        self.plot_index = QStandardItemModel()
        self.transform_graphs = QStandardItemModel()
        # Set ComboBox Models
        self.cb_flight_lines.setModel(self._flight.lines_model)
        self.cb_plot_index.setModel(self.plot_index)
        self.cb_plot_index.currentIndexChanged[int].connect(lambda idx: print("Index changed to %d" % idx))

        self.cb_transform_graphs.setModel(self.transform_graphs)

        # Initialize model for channels
        # TODO: This model should be of the transformed dataset not the flight data_model
        self.channels = QStandardItemModel()
        self.channels.itemChanged.connect(self._update_channel_selection)
        self.lv_channels.setModel(self.channels)

        # Populate ComboBox Models
        # self._set_flight_lines()

        for choice in ['Time', 'Latitude', 'Longitude']:
            item = QStandardItem(choice)
            item.setData(0, Qt.UserRole)
            self.plot_index.appendRow(item)

        self.cb_plot_index.setCurrentIndex(0)

        for choice, method in [('Airborne Post', AirbornePost)]:
            item = QStandardItem(choice)
            item.setData(method, Qt.UserRole)
            self.transform_graphs.appendRow(item)

        self.bt_execute_transform.clicked.connect(self.execute_transform)
        self.bt_select_all.clicked.connect(lambda: self._set_all_channels(Qt.Checked))
        self.bt_select_none.clicked.connect(lambda: self._set_all_channels(Qt.Unchecked))

        self.hlayout.addWidget(self._plot.widget, Qt.AlignLeft | Qt.AlignTop)

    @property
    def raw_gravity(self):
        return self._flight.gravity

    @property
    def raw_trajectory(self):
        return self._flight.trajectory

    @property
    def transform(self) -> QComboBox:
        return self.cb_transform_select

    @property
    def plot(self) -> TransformPlot:
        return self._plot

    def _set_all_channels(self, state=Qt.Checked):
        for i in range(self.channels.rowCount()):
            self.channels.item(i).setCheckState(state)

    def _update_channel_selection(self, item: QStandardItem):
        data = item.data(Qt.UserRole)
        if item.checkState() == Qt.Checked:
            self.plot.add_series(data)
        else:
            self.plot.remove_series(data)

    def _view_transform_graph(self):
        """Print out the dictionary transform (or even the raw code) in GUI?"""
        pass

    def execute_transform(self):
        if self.raw_trajectory is None or self.raw_gravity is None:
            self.log.warning("Missing trajectory or gravity")
            return

        self.log.info("Preparing Transformation Graph")
        transform = self.cb_transform_graphs.currentData(Qt.UserRole)

        graph = transform(self.raw_trajectory, self.raw_gravity, 0, 0)
        self.log.info("Executing graph")
        results = graph.execute()
        result_df = graph.result_df()

        default_channels = ['gravity']
        self.channels.clear()
        for col in result_df.columns:
            item = QStandardItem(col)
            item.setCheckable(True)
            item.setData(result_df[col], Qt.UserRole)
            self.channels.appendRow(item)
            if col in default_channels:
                item.setCheckState(Qt.Checked)

        # lat_idx = result_df.set_index('lat')
        # lon_idx = result_df.set_index('lon')


class TransformTab(BaseTab):
    """Sub-tab displayed within Flight tab interface. Displays interface for selecting
    Transform chains and plots for displaying the resultant data sets.
    """
    _name = "Transform"

    def __init__(self, label: str, flight):
        super().__init__(label, flight)

        self._layout = QVBoxLayout()
        self._layout.addWidget(TransformWidget(flight))
        self.setLayout(self._layout)

    def data_modified(self, action: str, dsrc):
        """Slot: Called when a DataSource has been added/removed from the
        Flight this tab/workspace is associated with."""
        if action.lower() == 'add':
            return
        elif action.lower() == 'remove':
            return
