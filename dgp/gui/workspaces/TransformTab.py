# -*- coding: utf-8 -*-

import logging
from enum import Enum, auto
from typing import List

import pandas as pd
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from dgp.core import AxisFormatter
from dgp.core.controllers.dataset_controller import DataSegmentController, DataSetController
from dgp.core.controllers.flight_controller import FlightController
from dgp.lib.transform.transform_graphs import SyncGravity, AirbornePost, TransformGraph
from dgp.gui.plotting.plotters import TransformPlot
from . import TaskTab
from ..ui.transform_tab_widget import Ui_TransformInterface


class TransformWidget(QWidget, Ui_TransformInterface):
    result = pyqtSignal()

    # User Roles for specific data within a channel
    TIME = 0x0101
    LATITUDE = 0x0102
    LONGITUDE = 0x103

    def __init__(self, flight: FlightController):
        super().__init__()
        self.setupUi(self)
        self.log = logging.getLogger(__name__)
        self._flight = flight
        self._dataset: DataSetController = flight.active_child
        self._plot = TransformPlot(rows=1)

        self._result: pd.DataFrame = None
        self.result.connect(self._on_result)

        # Line mask to view individual lines
        self._mask = None

        # Initialize Models for ComboBoxes
        self.plot_index = QStandardItemModel()
        self.transform_graphs = QStandardItemModel()
        # Set ComboBox Models
        self.qcb_mask.setModel(self._dataset.segment_model)
        self.qcb_plot_index.setModel(self.plot_index)
        self.qcb_transform_graphs.setModel(self.transform_graphs)

        self.qcb_plot_index.currentIndexChanged[int].connect(self._index_changed)

        # Initialize model for transformed channels
        self._channel_model = QStandardItemModel()
        self._channel_model.itemChanged.connect(self._update_channel_selection)
        self.qlv_channels.setModel(self._channel_model)

        self._index_map = {
            'Time': self.TIME,
            'Latitude': self.LATITUDE,
            'Longitude': self.LONGITUDE
        }
        for key, value in self._index_map.items():
            item = QStandardItem(key)
            item.setData(value, Qt.UserRole)
            self.plot_index.appendRow(item)

        self.qcb_plot_index.setCurrentIndex(0)

        for choice, method in [('Airborne Post', AirbornePost)]:
            item = QStandardItem(choice)
            item.setData(method, Qt.UserRole)
            self.transform_graphs.appendRow(item)

        self.qpb_execute_transform.clicked.connect(self.execute_transform)
        self.qpb_select_all.clicked.connect(lambda: self._set_all_channels(Qt.Checked))
        self.qpb_select_none.clicked.connect(lambda: self._set_all_channels(Qt.Unchecked))
        self.qtb_set_mask.clicked.connect(self._set_mask)
        self.qtb_clear_mask.clicked.connect(self._clear_mask)
        self.qpb_stack_lines.clicked.connect(self._stack_lines)

        self.hlayout.addWidget(self._plot.widget, Qt.AlignLeft | Qt.AlignTop)

    @property
    def raw_gravity(self) -> pd.DataFrame:
        return self._dataset.gravity

    @property
    def raw_trajectory(self) -> pd.DataFrame:
        return self._dataset.trajectory

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataset.dataframe()

    @property
    def plot(self) -> TransformPlot:
        return self._plot

    @property
    def _channels(self) -> List[QStandardItem]:
        return [self._channel_model.item(i)
                for i in range(self._channel_model.rowCount())]

    @property
    def _segments(self) -> List[DataSegmentController]:
        return [self._dataset.segment_model.item(i)
                for i in range(self._dataset.segment_model.rowCount())]

    def _auto_range(self):
        """Call autoRange on all plot surfaces to scale the view to its
        contents"""
        for plot in self.plot.plots:
            plot.autoRange()

    def _view_transform_graph(self):
        """Print out the dictionary transform (or even the raw code) in GUI?"""
        pass

    def _set_mask(self):
        # TODO: Decide whether this is useful to allow viewing of a single line
        # segment
        pass

    def _clear_mask(self):
        pass

    def _split_by_segment(self, segments: List[DataSegmentController], series):

        pass

    def _stack_lines(self):
        """Experimental feature, currently works to plot only FAC vs Lon

        TODO: Maybe make stacked lines a toggleable mode
        TODO: Need to be more general and work on all transforms/channels
        """
        if self._result is None:
            self.log.warning(f'Transform result not yet computed')
            return

        channels = []
        for channel in self._channels:
            if channel.checkState() == Qt.Checked:
                channels.append(channel)
            # channel.setCheckState(Qt.Unchecked)
        if not len(channels):
            self.log.error("No channel selected.")
            return

        # series = channels.pop()
        # TODO: Make this a class property
        xindex = self.qcb_plot_index.currentData(Qt.UserRole)

        for segment in self._segments:
            start = segment.get_attr('start')
            stop = segment.get_attr('stop')
            start_idx = self._result.index.searchsorted(start)
            stop_idx = self._result.index.searchsorted(stop)
            self.log.debug(f'Start idx {start_idx} stop idx {stop_idx}')

            for channel in channels:
                # Stack only a single channel for the moment
                segment_series = channel.data(xindex).iloc[start_idx:stop_idx]
                segment_series.name = f'{channel.text()} - {segment.get_attr("sequence")}'
                self.plot.add_series(segment_series)

        self._auto_range()

    def _set_all_channels(self, state=Qt.Checked):
        for i in range(self._channel_model.rowCount()):
            self._channel_model.item(i).setCheckState(state)

    def _update_channel_selection(self, item: QStandardItem):
        xindex = self.qcb_plot_index.currentData(Qt.UserRole)
        data = item.data(xindex)
        if item.checkState() == Qt.Checked:
            self.plot.add_series(data)
        else:
            self.plot.remove_series(data)
        self._auto_range()

    @pyqtSlot(int, name='_index_changed')
    def _index_changed(self, index: int):
        self.log.debug(f'X-Axis changed to {self.qcb_plot_index.currentText()}')
        if self._result is None:
            return

        self.plot.clear()
        for channel in self._channels:
            if channel.checkState() == Qt.Checked:
                channel.setCheckState(Qt.Unchecked)
                channel.setCheckState(Qt.Checked)

        self._auto_range()

    @pyqtSlot(name='_on_result')
    def _on_result(self):
        default_channels = ['fac']

        time_df = self._result
        lat_df = time_df.set_index('lat')
        lon_df = time_df.set_index('lon')

        self._channel_model.clear()
        for col in sorted(time_df.columns):
            item = QStandardItem(col)
            item.setCheckable(True)
            item.setData(time_df[col], self.TIME)
            if col == 'lat':
                item.setData(pd.Series(), self.LATITUDE)
            else:
                item.setData(lat_df[col], self.LATITUDE)

            if col == 'lon':
                item.setData(pd.Series(), self.LONGITUDE)
            else:
                item.setData(lon_df[col], self.LONGITUDE)
            self._channel_model.appendRow(item)
            if col in default_channels:
                item.setCheckState(Qt.Checked)

    def execute_transform(self):
        gravity = self.raw_gravity
        trajectory = self.raw_trajectory
        if gravity.empty or trajectory.empty:
            self.log.warning("Missing trajectory or gravity")
            return

        transform = self.qcb_transform_graphs.currentData(Qt.UserRole)
        graph = transform(trajectory, gravity, 0, 0)
        self.log.info("Executing graph")
        graph.execute()
        self._result = graph.result_df()
        self.result.emit()


class TransformTab(TaskTab):
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
