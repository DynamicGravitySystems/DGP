# -*- coding: utf-8 -*-
import logging

import pandas as pd

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QDockWidget, QWidget, QListView, QSizePolicy
import PyQt5.QtWidgets as QtWidgets

from dgp.core.controllers.flightline_controller import FlightLineController
from dgp.core.models.flight import FlightLine
from gui.widgets.channel_select_widget import ChannelSelectWidget
from . import BaseTab
from dgp.core.controllers.flight_controller import FlightController
from dgp.gui.plotting.plotters import LineUpdate, PqtLineSelectPlot


class PlotTab(BaseTab):
    """Sub-tab displayed within Flight tab interface. Displays canvas for
    plotting data series."""
    _name = "Line Selection"
    defaults = {'gravity': 0, 'long': 1, 'cross': 1}

    def __init__(self, label: str, flight: FlightController, axes: int,
                 plot_default=True, **kwargs):
        super().__init__(label, flight, **kwargs)
        self.log = logging.getLogger('PlotTab')
        self._ctrl_widget = None
        self._axes_count = axes
        self.plot = PqtLineSelectPlot(rows=2)
        self.plot.line_changed.connect(self._on_modified_line)
        # self._channel_select = ChannelSelectDialog(flight.data_model, plots=1, parent=self)
        self._setup_ui()

    def _setup_ui(self):
        qhbl_main = QHBoxLayout()
        qvbl_plot_layout = QVBoxLayout()
        qhbl_top_buttons = QHBoxLayout()
        self._qpb_channel_toggle = QtWidgets.QPushButton("Data Channels")
        self._qpb_channel_toggle.setCheckable(True)
        self._qpb_channel_toggle.setChecked(True)
        qhbl_top_buttons.addWidget(self._qpb_channel_toggle,
                                   alignment=Qt.AlignLeft)

        self._mode_label = QtWidgets.QLabel('')
        # top_button_hlayout.addSpacing(20)
        qhbl_top_buttons.addStretch(2)
        qhbl_top_buttons.addWidget(self._mode_label)
        qhbl_top_buttons.addStretch(2)
        # top_button_hlayout.addSpacing(20)
        self._qpb_toggle_mode = QtWidgets.QPushButton("Toggle Line Selection Mode")
        self._qpb_toggle_mode.setCheckable(True)
        self._qpb_toggle_mode.toggled.connect(self._toggle_selection)
        qhbl_top_buttons.addWidget(self._qpb_toggle_mode,
                                   alignment=Qt.AlignRight)
        qvbl_plot_layout.addLayout(qhbl_top_buttons)

        # TODO Re-enable this
        # for line in self.flight.lines:
        #     self.plot.add_patch(line.start, line.stop, line.uid, line.label)

        channel_widget = ChannelSelectWidget(self.flight.data_model)
        channel_widget.channel_added.connect(self._channel_added)
        channel_widget.channel_removed.connect(self._channel_removed)
        channel_widget.channels_cleared.connect(self._clear_plot)

        self.plot.widget.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        qvbl_plot_layout.addWidget(self.plot.widget)
        dock_widget = QDockWidget("Channels")
        dock_widget.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred))
        dock_widget.setWidget(channel_widget)
        self._qpb_channel_toggle.toggled.connect(dock_widget.setVisible)
        qhbl_main.addItem(qvbl_plot_layout)
        qhbl_main.addWidget(dock_widget)
        self.setLayout(qhbl_main)

    def _channel_added(self, plot: int, item: QStandardItem):
        self.plot.add_series(item.data(Qt.UserRole), plot)

    def _channel_removed(self, plot: int, item: QStandardItem):
        self.plot.remove_series(item.data(Qt.UserRole))

    def _clear_plot(self):
        print("Clearing plot")

    def _toggle_selection(self, state: bool):
        self.plot.selection_mode = state
        if state:
            self._mode_label.setText("<h2><b>Line Selection Active</b></h2>")
        else:
            self._mode_label.setText("")

    def set_defaults(self, channels):
        for name, plot in self.defaults.items():
            for channel in channels:
                if channel.field == name.lower():
                    self.model.move_channel(channel.uid, plot)

    def _on_modified_line(self, update: LineUpdate):
        # TODO: Update this to work with new project
        print(update)
        start = update.start
        stop = update.stop
        try:
            if isinstance(update.start, pd.Timestamp):
                start = start.timestamp()
            if isinstance(stop, pd.Timestamp):
                stop = stop.timestamp()
        except OSError:
            print("Error converting Timestamp to float POSIX timestamp")
            return

        if update.uid in [x.uid for x in self.flight.lines]:
            if update.action == 'modify':
                line: FlightLineController = self.flight.get_child(update.uid)
                line.update_line(start, stop, update.label)
                self.log.debug("Modified line: start={start}, stop={stop},"
                               " label={label}"
                               .format(start=start, stop=stop,
                                       label=update.label))
            elif update.action == 'remove':
                line = self.flight.get_child(update.uid)  # type: FlightLineController
                if line is None:
                    self.log.warning("Couldn't retrieve FlightLine from Flight for removal")
                    return
                self.flight.remove_child(line.proxied, line.row(), confirm=False)
                self.log.debug("Removed line: start={start}, "
                               "stop={stop}, label={label}"
                               .format(start=start, stop=stop,
                                       label=update.label))
        else:
            line = FlightLine(start, stop, 0, uid=update.uid)
            # line = types.FlightLine(update.start, update.stop, uid=update.uid)
            self.flight.add_child(line)
            self.log.debug("Added line to flight {flt}: start={start}, "
                           "stop={stop}, label={label}, uid={uid}"
                           .format(flt=self.flight.name, start=start,
                                   stop=stop, label=update.label,
                                   uid=line.uid))
