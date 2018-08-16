# -*- coding: utf-8 -*-
import inspect
import logging
from enum import Enum, auto
from typing import List

import pandas as pd
from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QWidget, QTextEdit

from dgp.core.controllers.dataset_controller import DataSetController, DataSegmentController
from dgp.gui.plotting.backends import AxisFormatter
from dgp.gui.plotting.plotters import TransformPlot
from dgp.gui.ui.transform_tab_widget import Ui_TransformInterface
from dgp.lib.transform.graph import TransformGraph
from dgp.lib.transform.transform_graphs import AirbornePost

try:
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import HtmlFormatter
    HAS_HIGHLIGHTER = True
except ImportError:
    HAS_HIGHLIGHTER = False


class _Mode(Enum):
    NORMAL = auto()
    SEGMENTS = auto()


class TransformWidget(QWidget, Ui_TransformInterface):
    result = pyqtSignal()

    # User Roles for specific data within a channel
    TIME = 0x0101
    LATITUDE = 0x0102
    LONGITUDE = 0x103

    def __init__(self, dataset: DataSetController, plotter: TransformPlot):
        super().__init__()
        self.setupUi(self)
        self.log = logging.getLogger(__name__)
        self._dataset: DataSetController = dataset
        self._plot = plotter
        self._mode = _Mode.NORMAL
        self._segment_indexes = {}

        self._result: pd.DataFrame = None
        self.result.connect(self._on_result)

        # Line mask to view individual lines
        self._mask = None

        # Initialize Models for ComboBoxes
        self.plot_index = QStandardItemModel()
        self.transform_graphs = QStandardItemModel()
        # Set ComboBox Models
        self.qcb_plot_index.setModel(self.plot_index)
        self.qcb_transform_graphs.setModel(self.transform_graphs)
        self.qcb_transform_graphs.currentIndexChanged.connect(self._graph_source)

        self.qcb_plot_index.currentIndexChanged[int].connect(self._index_changed)

        # Initialize model for transformed channels
        self._channel_model = QStandardItemModel()
        self._channel_model.itemChanged.connect(self._channel_state_changed)
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
        self.qpb_toggle_mode.clicked.connect(self._mode_toggled)
        self.qte_source_browser.setReadOnly(True)
        self.qte_source_browser.setLineWrapMode(QTextEdit.NoWrap)

    @property
    def xaxis_index(self) -> int:
        return self.qcb_plot_index.currentData(Qt.UserRole)

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
    def transform(self) -> TransformGraph:
        return self.qcb_transform_graphs.currentData(Qt.UserRole)

    @property
    def _channels(self) -> List[QStandardItem]:
        return [self._channel_model.item(i)
                for i in range(self._channel_model.rowCount())]

    @property
    def _segments(self) -> List[DataSegmentController]:
        return [self._dataset.segment_model.item(i)
                for i in range(self._dataset.segment_model.rowCount())]

    def _graph_source(self, index):  # pragma: no cover
        """Utility to display the transform graph source (__init__) method
        containing the definition for the graph.

        If Pygments is available the source code will be highlighted

        Notes
        -----
        The inspection of the source code is somewhat fragile and dependent on
        the way the graph is defined in the source. The current method gets the
        __init__ source code for the TransformGraph descendant then searches for
        the string index of 'self.transform_graph', and takes from the first '{'
        until the first '}'.

        """
        graph = self.transform
        src = inspect.getsource(graph.__init__)
        start_str = 'self.transform_graph'
        start_i = src.find('{', src.find(start_str)) + 1
        src = src[start_i:src.find('}')]
        trimmed = map(lambda x: x.lstrip(' '), src.split('\n'))
        src = ''
        for line in trimmed:
            src += f'{line}\n'

        if HAS_HIGHLIGHTER:
            css = HtmlFormatter().get_style_defs('.highlight')
            style_block = f'<style>{css}</style>'
            html = highlight(src, PythonLexer(stripall=True), HtmlFormatter())
            self.qte_source_browser.setHtml(f'{style_block}{html}')
        else:
            self.qte_source_browser.setText(src)

    def _mode_toggled(self):
        """Toggle the mode state between Normal or Segments"""
        self._set_all_channels(state=Qt.Unchecked)
        if self._mode is _Mode.NORMAL:
            self._mode = _Mode.SEGMENTS
        else:
            self._mode = _Mode.NORMAL
        self.log.debug(f'Changed mode to {self._mode}')
        return

    def _set_all_channels(self, state=Qt.Checked):
        for i in range(self._channel_model.rowCount()):
            self._channel_model.item(i).setCheckState(state)

    def _add_series(self, series: pd.Series, row=0):
        if self._mode is _Mode.NORMAL:
            self._plot.add_series(series, row)
        elif self._mode is _Mode.SEGMENTS:
            self._segment_indexes[series.name] = []
            for i, segment in enumerate(self._segments):
                start_i = self._result.index.searchsorted(segment.get_attr('start'))
                stop_i = self._result.index.searchsorted(segment.get_attr('stop'))
                seg_data = series.iloc[start_i:stop_i]

                seg_data.name = f'{series.name}-{segment.get_attr("label") or i}'
                self._segment_indexes[series.name].append(seg_data.name)
                self._plot.add_series(seg_data, row=0)

    def _remove_series(self, series: pd.Series):
        if self._mode is _Mode.NORMAL:
            self._plot.remove_series(series.name, row=0)
        elif self._mode is _Mode.SEGMENTS:
            for name in self._segment_indexes[series.name]:
                self._plot.remove_series(name, row=0)
            del self._segment_indexes[series.name]

    def _channel_state_changed(self, item: QStandardItem):
        data: pd.Series = item.data(self.xaxis_index)
        if item.checkState() == Qt.Checked:
            self._add_series(data, row=0)
        else:
            self._remove_series(data)

    @pyqtSlot(int, name='_index_changed')
    def _index_changed(self, index: int):
        self.log.debug(f'X-Axis changed to {self.qcb_plot_index.currentText()}')
        if self._result is None:
            return
        if self.xaxis_index in {self.LATITUDE, self.LONGITUDE}:
            self._plot.set_axis_formatters(AxisFormatter.SCALAR)
        else:
            self._plot.set_axis_formatters(AxisFormatter.DATETIME)

        for channel in self._channels:
            if channel.checkState() == Qt.Checked:
                channel.setCheckState(Qt.Unchecked)
                channel.setCheckState(Qt.Checked)

    @pyqtSlot(name='_on_result')
    def _on_result(self):
        """_on_result called when Transformation DataFrame has been computed.

        This method creates the channel objects for the interface.
        """
        default_channels = ['fac']

        time_df = self._result
        lat_df = time_df.set_index('lat')
        lon_df = time_df.set_index('lon')

        for i in range(self._channel_model.rowCount()):
            item = self._channel_model.item(i)
            del item

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
        del self._result
        self._result = graph.result_df()
        self.result.emit()
