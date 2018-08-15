# -*- coding: utf-8 -*-
import logging

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QDockWidget, QSizePolicy, QAction

from dgp.core import StateAction, Icon
from dgp.gui.widgets.channel_select_widget import ChannelSelectWidget
from dgp.core.controllers.flight_controller import FlightController
from dgp.gui.plotting.plotters import LineUpdate, LineSelectPlot
from dgp.gui.plotting.backends import Axis
from .TaskTab import TaskTab


class PlotTab(TaskTab):
    """Sub-tab displayed within Flight tab interface. Displays canvas for
    plotting data series.

    Parameters
    ----------
    label : str
    flight : FlightController

    """

    def __init__(self, label: str, flight: FlightController, **kwargs):
        # TODO: It may make more sense to associate a DataSet with the plot vs a Flight
        super().__init__(label, root=flight, **kwargs)
        self.log = logging.getLogger(__name__)
        self._dataset = flight.active_child

        self._plot = LineSelectPlot(rows=2)
        self._plot.sigSegmentChanged.connect(self._on_modified_line)

        for segment in self._dataset.segments:
            group = self._plot.add_segment(segment.get_attr('start'),
                                           segment.get_attr('stop'),
                                           segment.get_attr('label'),
                                           segment.uid, emit=False)
            segment.add_reference(group)

        # Create/configure the tab layout/widgets/controls
        qhbl_main_layout = QHBoxLayout()
        qvbl_plot_layout = QVBoxLayout()
        qhbl_main_layout.addItem(qvbl_plot_layout)
        self.toolbar = self._plot.get_toolbar(self)
        # self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        qvbl_plot_layout.addWidget(self.toolbar, alignment=Qt.AlignLeft)
        qvbl_plot_layout.addWidget(self._plot)

        # Toggle control to hide/show data channels dock
        qa_channel_toggle = QAction(Icon.PLOT_LINE.icon(), "Data Channels", self)
        qa_channel_toggle.setCheckable(True)
        qa_channel_toggle.setChecked(True)
        self.toolbar.addAction(qa_channel_toggle)

        # Load data channel selection widget
        channel_widget = ChannelSelectWidget(self._dataset.series_model)
        channel_widget.channel_added.connect(self._channel_added)
        channel_widget.channel_removed.connect(self._channel_removed)
        channel_widget.channels_cleared.connect(self._plot.clear)

        dock_widget = QDockWidget("Channels")
        dock_widget.setFeatures(QDockWidget.NoDockWidgetFeatures)
        dock_widget.setSizePolicy(QSizePolicy(QSizePolicy.Maximum,
                                              QSizePolicy.Preferred))
        dock_widget.setWidget(channel_widget)
        qa_channel_toggle.toggled.connect(dock_widget.setVisible)
        qhbl_main_layout.addWidget(dock_widget)
        self.setLayout(qhbl_main_layout)

    def _channel_added(self, row: int, item: QStandardItem):
        series: pd.Series = item.data(Qt.UserRole)
        if series.max(skipna=True) < 1000:
            axis = Axis.RIGHT
        else:
            axis = Axis.LEFT
        self._plot.add_series(item.data(Qt.UserRole), row, axis=axis)

    def _channel_removed(self, item: QStandardItem):
        series: pd.Series = item.data(Qt.UserRole)
        indexes = self._plot.find_series(series.name)
        for index in indexes:
            self._plot.remove_series(*index)

    def _on_modified_line(self, update: LineUpdate):
        if update.action is StateAction.DELETE:
            self._dataset.remove_segment(update.uid)
            return

        start: pd.Timestamp = update.start
        stop: pd.Timestamp = update.stop
        assert isinstance(start, pd.Timestamp)
        assert isinstance(stop, pd.Timestamp)

        if update.action is StateAction.UPDATE:
            self._dataset.update_segment(update.uid, start, stop, update.label)
        else:
            seg = self._dataset.add_segment(update.uid, start, stop, update.label)
            seg.add_reference(self._plot.get_segment(seg.uid))
