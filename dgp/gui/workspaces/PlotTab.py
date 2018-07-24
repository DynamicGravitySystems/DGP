# -*- coding: utf-8 -*-
import logging

import pandas as pd

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QDockWidget, QSizePolicy
import PyQt5.QtWidgets as QtWidgets

from dgp.gui.widgets.channel_select_widget import ChannelSelectWidget
from dgp.core.controllers.flight_controller import FlightController
from dgp.gui.plotting.plotters import LineUpdate, PqtLineSelectPlot
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
        # TODO: It will make more sense to associate a DataSet with the plot vs a Flight
        super().__init__(label, flight, **kwargs)
        self.log = logging.getLogger(__name__)
        self._dataset = flight.get_active_dataset()
        self.plot: PqtLineSelectPlot = PqtLineSelectPlot(rows=2)
        self.plot.line_changed.connect(self._on_modified_line)
        self._setup_ui()

        # TODO:There should also be a check to ensure that the lines are within the bounds of the data
        # Huge slowdowns occur when trying to plot a FlightLine and a channel when the points are weeks apart
        # for line in flight.lines:
        #     self.plot.add_linked_selection(line.start.timestamp(), line.stop.timestamp(), uid=line.uid, emit=False)

    def _setup_ui(self):
        qhbl_main = QHBoxLayout()
        qvbl_plot_layout = QVBoxLayout()
        qhbl_top_buttons = QHBoxLayout()
        self._qpb_channel_toggle = QtWidgets.QPushButton("Data Channels")
        self._qpb_channel_toggle.setCheckable(True)
        self._qpb_channel_toggle.setChecked(True)
        qhbl_top_buttons.addWidget(self._qpb_channel_toggle,
                                   alignment=Qt.AlignLeft)

        self._ql_mode = QtWidgets.QLabel('')
        # top_button_hlayout.addSpacing(20)
        qhbl_top_buttons.addStretch(2)
        qhbl_top_buttons.addWidget(self._ql_mode)
        qhbl_top_buttons.addStretch(2)
        # top_button_hlayout.addSpacing(20)
        self._qpb_toggle_mode = QtWidgets.QPushButton("Toggle Line Selection Mode")
        self._qpb_toggle_mode.setCheckable(True)
        self._qpb_toggle_mode.toggled.connect(self._toggle_selection)
        qhbl_top_buttons.addWidget(self._qpb_toggle_mode,
                                   alignment=Qt.AlignRight)
        qvbl_plot_layout.addLayout(qhbl_top_buttons)

        channel_widget = ChannelSelectWidget(self._dataset.series_model)
        self.log.debug(f'Dataset is {self._dataset!s} with {self._dataset.series_model.rowCount()} rows')
        channel_widget.channel_added.connect(self._channel_added)
        channel_widget.channel_removed.connect(self._channel_removed)
        channel_widget.channels_cleared.connect(self._clear_plot)

        self.plot.widget.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                   QSizePolicy.Expanding))
        qvbl_plot_layout.addWidget(self.plot.widget)
        dock_widget = QDockWidget("Channels")
        dock_widget.setSizePolicy(QSizePolicy(QSizePolicy.Maximum,
                                              QSizePolicy.Preferred))
        dock_widget.setWidget(channel_widget)
        self._qpb_channel_toggle.toggled.connect(dock_widget.setVisible)
        qhbl_main.addItem(qvbl_plot_layout)
        qhbl_main.addWidget(dock_widget)
        self.setLayout(qhbl_main)

    def _channel_added(self, plot: int, item: QStandardItem):
        self.plot.add_series(item.data(Qt.UserRole), plot)

    def _channel_removed(self, item: QStandardItem):
        self.plot.remove_series(item.data(Qt.UserRole))

    def _clear_plot(self):
        self.plot.clear()

    def _toggle_selection(self, state: bool):
        self.plot.selection_mode = state
        if state:
            self._ql_mode.setText("<h2><b>Line Selection Active</b></h2>")
        else:
            self._ql_mode.setText("")

    def _on_modified_line(self, update: LineUpdate):
        start = update.start
        stop = update.stop
        try:
            if isinstance(update.start, pd.Timestamp):
                start = start.timestamp()
            if isinstance(stop, pd.Timestamp):
                stop = stop.timestamp()
        except OSError:
            self.log.exception("Error converting Timestamp to float POSIX timestamp")
            return

        if update.action == 'modify':
            self._dataset.update_segment(update.uid, start, stop, update.label)
        elif update.action == 'remove':
            self._dataset.remove_segment(update.uid)
        else:
            self._dataset.add_segment(update.uid, start, stop, update.label)
