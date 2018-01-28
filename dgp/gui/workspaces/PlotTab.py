# coding: utf-8

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
import PyQt5.QtWidgets as QtWidgets

from . import BaseTab, Flight
import dgp.gui.models as models
import dgp.lib.types as types
from dgp.gui.dialogs import ChannelSelectionDialog
from dgp.gui.plotting.plotters import LineGrabPlot, LineUpdate, PqtLineSelectPlot


class PlotTab(BaseTab):
    """Sub-tab displayed within Flight tab interface. Displays canvas for
    plotting data series."""
    _name = "Line Selection"
    defaults = {'gravity': 0, 'long': 1, 'cross': 1}

    def __init__(self, label: str, flight: Flight, axes: int,
                 plot_default=True, **kwargs):
        super().__init__(label, flight, **kwargs)
        self.log = logging.getLogger('PlotTab')
        self._ctrl_widget = None
        self._axes_count = axes
        self._setup_ui()
        self._init_model(plot_default)

    def _setup_ui(self):
        vlayout = QVBoxLayout()
        top_button_hlayout = QHBoxLayout()
        self._select_channels = QtWidgets.QPushButton("Select Channels")
        self._select_channels.clicked.connect(self._show_select_dialog)
        top_button_hlayout.addWidget(self._select_channels,
                                     alignment=Qt.AlignLeft)

        self._mode_label = QtWidgets.QLabel('')
        # top_button_hlayout.addSpacing(20)
        top_button_hlayout.addStretch(2)
        top_button_hlayout.addWidget(self._mode_label)
        top_button_hlayout.addStretch(2)
        # top_button_hlayout.addSpacing(20)
        self._toggle_mode = QtWidgets.QPushButton("Toggle Line Selection Mode")
        self._toggle_mode.setCheckable(True)
        self._toggle_mode.toggled.connect(self._toggle_selection)
        top_button_hlayout.addWidget(self._toggle_mode,
                                     alignment=Qt.AlignRight)
        vlayout.addLayout(top_button_hlayout)

        # self.plot = LineGrabPlot(self.flight, self._axes_count)
        self.plot = PqtLineSelectPlot(flight=self.flight, rows=3)
        for line in self.flight.lines:
            self.plot.add_patch(line.start, line.stop, line.uid, line.label)
        self.plot.line_changed.connect(self._on_modified_line)

        vlayout.addWidget(self.plot.widget)
        # vlayout.addWidget(self.plot.get_toolbar(), alignment=Qt.AlignBottom)
        self.setLayout(vlayout)

    def _init_model(self, default_state=False):
        channels = self.flight.channels
        plot_model = models.ChannelListModel(channels, len(self.plot))
        plot_model.plotOverflow.connect(self._too_many_children)
        plot_model.channelChanged.connect(self._on_channel_changed)
        self.model = plot_model

        if default_state:
            self.set_defaults(channels)

    def _toggle_selection(self, state: bool):
        self.plot.selection_mode = state
        if state:
            # self._toggle_mode.setText("Exit Line Selection Mode")
            self._mode_label.setText("<h2><b>Line Selection Active</b></h2>")
        else:
            # self._toggle_mode.setText("Enter Line Selection Mode")
            self._mode_label.setText("")

    def set_defaults(self, channels):
        for name, plot in self.defaults.items():
            for channel in channels:
                if channel.field == name.lower():
                    self.model.move_channel(channel.uid, plot)

    def _show_select_dialog(self):
        dlg = ChannelSelectionDialog(parent=self)
        if self.model is not None:
            dlg.set_model(self.model)
        dlg.show()

    def data_modified(self, action: str, dsrc: types.DataSource):
        if action.lower() == 'add':
            self.log.info("Adding channels to model.")
            n_channels = dsrc.get_channels()
            self.model.add_channels(*n_channels)
            self.set_defaults(n_channels)
        elif action.lower() == 'remove':
            self.log.info("Removing channels from model.")
            # Re-initialize model - source must be removed from flight first
            self._init_model()
        else:
            return

    def _on_modified_line(self, info: LineUpdate):
        if info.uid in [x.uid for x in self.flight.lines]:
            if info.action == 'modify':
                line = self.flight.get_line(info.uid)
                line.start = info.start
                line.stop = info.stop
                line.label = info.label
                self.log.debug("Modified line: start={start}, stop={stop},"
                               " label={label}"
                               .format(start=info.start, stop=info.stop,
                                       label=info.label))
            elif info.action == 'remove':
                self.flight.remove_line(info.uid)
                self.log.debug("Removed line: start={start}, "
                               "stop={stop}, label={label}"
                               .format(start=info.start, stop=info.stop,
                                       label=info.label))
        else:
            line = types.FlightLine(info.start, info.stop, uid=info.uid)
            self.flight.add_line(line)
            self.log.debug("Added line to flight {flt}: start={start}, "
                           "stop={stop}, label={label}, uid={uid}"
                           .format(flt=self.flight.name, start=info.start,
                                   stop=info.stop, label=info.label,
                                   uid=line.uid))

    def _on_channel_changed(self, new: int, channel: types.DataChannel):
        self.plot.remove_series(channel.series())
        if new != -1:
            try:
                self.plot.add_series(channel.series(), new)
            except:
                self.log.exception("Error adding series to plot")
        self.model.update()

    def _too_many_children(self, uid):
        self.log.warning("Too many children for plot: {}".format(uid))
