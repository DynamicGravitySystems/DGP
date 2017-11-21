# coding: utf-8

# Class for custom Qt Widgets

import logging

from PyQt5.QtGui import QDropEvent, QDragEnterEvent, QDragMoveEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from PyQt5.QtCore import QMimeData, Qt

from dgp.lib.plotter import LineGrabPlot, PlotCurve, LineUpdate
from dgp.lib.project import Flight


# Experimenting with drag-n-drop and custom widgets
class DropTarget(QWidget):

    def dragEnterEvent(self, event: QDragEnterEvent):
        event.acceptProposedAction()
        print("Drag entered")

    def dragMoveEvent(self, event: QDragMoveEvent):
        event.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        print("Drop detected")
        # mime = e.mimeData()  # type: QMimeData


class FlightTab(QWidget):
    def __init__(self, flight: Flight, parent=None, flags=0, **kwargs):
        super().__init__(parent=parent, flags=Qt.Widget)
        self.log = logging.getLogger(__name__)
        self._flight = flight

        self._layout = QVBoxLayout(self)
        self._workspace = QTabWidget()
        self._workspace.setTabPosition(QTabWidget.West)
        self._layout.addWidget(self._workspace)

        # Define Sub-Tabs within Flight space e.g. Plot, Transform, Maps
        self._plot_tab = QWidget()
        self._plot = self._init_plot_tab(flight)
        self.update_plot()
        self._transform_tab = QWidget()
        self._map_tab = QWidget()

        self._workspace.addTab(self._plot_tab, "Plot")
        self._workspace.addTab(self._transform_tab, "Transforms")
        self._workspace.addTab(self._map_tab, "Map")

        self._workspace.setCurrentIndex(0)

    def _init_plot_tab(self, flight) -> LineGrabPlot:
        plot_layout = QVBoxLayout()
        plot = LineGrabPlot(flight, 3)
        plot.line_changed.connect(self._on_modified_line)
        # plot_layout.addWidget(plot, alignment=Qt.AlignCenter)
        plot_layout.addWidget(plot)
        plot_layout.addWidget(plot.get_toolbar(), alignment=Qt.AlignLeft)
        self._plot_tab.setLayout(plot_layout)

        return plot

    def _init_transform_tab(self):
        pass

    def _init_map_tab(self):
        pass

    def _on_modified_line(self, info: LineUpdate):
        flight = self._flight
        if info.uid in [x.uid for x in flight.lines]:
            if info.action == 'modify':
                line = flight.lines[info.uid]
                line.start = info.start
                line.stop = info.stop
                line.label = info.label
                self.log.debug("Modified line: start={start}, stop={stop},"
                               " label={label}"
                               .format(start=info.start, stop=info.stop,
                                       label=info.label))
            elif info.action == 'remove':
                flight.remove_line(info.uid)
                self.log.debug("Removed line: start={start}, "
                               "stop={stop}, label={label}"
                               .format(start=info.start, stop=info.stop,
                                       label=info.label))
        else:
            flight.add_line(info.start, info.stop, uid=info.uid)
            self.log.debug("Added line to flight {flt}: start={start}, "
                           "stop={stop}, label={label}"
                           .format(flt=flight.name, start=info.start,
                                   stop=info.stop, label=info.label))

    def update_plot(self):
        self._plot.clear()  # Do we really want to do this?

        state = self._flight.get_plot_state()
        draw = False
        for channel in state:
            label, axes = state[channel]
            curve = PlotCurve(channel, self._flight.get_channel_data(channel),
                              label, axes)
            self._plot.add_series(curve, propogate=False)

        for line in self._flight.lines:
            self._plot.draw_patch(line.start, line.stop, line.uid)
            draw = True
        if draw:
            self._plot.draw()

    @property
    def flight(self):
        return self._flight

    @property
    def plot(self):
        return self._plot
