# coding: utf-8

# Class for custom Qt Widgets

import logging

from PyQt5.QtGui import QDropEvent, QDragEnterEvent, QDragMoveEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from PyQt5.QtCore import QMimeData, Qt, pyqtSignal, pyqtBoundSignal

from dgp.lib.plotter import LineGrabPlot, LineUpdate
from dgp.lib.project import Flight
import dgp.gui.models as models
import dgp.lib.types as types
from dgp.lib.etc import gen_uuid


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


class WorkspaceWidget(QWidget):
    """Base Workspace Tab Widget - Subclass to specialize function"""
    def __init__(self, label: str, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.label = label
        self._uid = gen_uuid('ww')
        # self._layout = layout
        self._context_model = None
        # self.setLayout(self._layout)

    def data_modified(self, action: str, uid: str):
        pass

    @property
    def model(self):
        return self._context_model

    @model.setter
    def model(self, value):
        assert isinstance(value, models.BaseTreeModel)
        self._context_model = value

    @property
    def uid(self):
        return self._uid


class PlotTab(WorkspaceWidget):
    """Sub-tab displayed within Flight tab interface. Displays canvas for
    plotting data series."""
    def __init__(self, flight, label, axes: int, **kwargs):
        super().__init__(label, **kwargs)
        self.log = logging.getLogger('PlotTab')

        vlayout = QVBoxLayout()
        self._plot = LineGrabPlot(flight, axes)
        self._plot.line_changed.connect(self._on_modified_line)
        self._flight = flight

        vlayout.addWidget(self._plot)
        vlayout.addWidget(self._plot.get_toolbar())
        self.setLayout(vlayout)
        self._init_model()

    def _init_model(self):
        channels = list(self._flight.channels)
        plot_model = models.ChannelListModel(channels, len(self._plot))
        plot_model.plotOverflow.connect(self._too_many_children)
        plot_model.channelChanged.connect(self._on_channel_changed)
        plot_model.update()
        self.model = plot_model

    def data_modified(self, action: str, uid: str):
        self.log.info("Adding channels to model.")
        channels = list(self._flight.channels)
        for cn in channels:
            self.model.append_channel(cn)
        self.model.update()
        # self._init_model()

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

    def _on_channel_changed(self, new, old, channel: types.DataChannel):
        self.log.info("Channel change request: new{} old{}".format(new, old))
        if new == -1:
            self.log.debug("Removing series from plot")
            self._plot.remove_series(channel)
            return
        if old == -1:
            self.log.info("Adding series to plot")
            self._plot.add_series(channel, new)
            return
        self.log.debug("Moving series on plot")
        # self._plot.move_series(channel.uid, new)
        self._plot.remove_series(channel)
        self._plot.add_series(channel, new)
        return

    # # TODO: Change conflicting name
    # def _update(self):
    #     self._plot.clear()  # Do we really want to do this?
    #
    #     state = self._flight.get_plot_state()
    #     draw = False
    #     for channel in state:
    #         dc = state[channel]  # type: types.DataChannel
    #         self._plot.add_series(dc, dc.axes)
    #
    #     for line in self._flight.lines:
    #         self._plot.draw_patch(line.start, line.stop, line.uid)
    #         draw = True
    #     if draw:
    #         self._plot.draw()

    def _too_many_children(self, uid):
        self.log.warning("Too many children for plot: {}".format(uid))


class TransformTab(WorkspaceWidget):
    pass


class MapTab(WorkspaceWidget):
    pass


class FlightTab(QWidget):

    contextChanged = pyqtSignal(models.BaseTreeModel)  # type: pyqtBoundSignal

    def __init__(self, flight: Flight, parent=None, flags=0, **kwargs):
        super().__init__(parent=parent, flags=Qt.Widget)
        self.log = logging.getLogger(__name__)
        self._flight = flight

        self._layout = QVBoxLayout(self)
        self._workspace = QTabWidget()
        self._workspace.setTabPosition(QTabWidget.West)
        self._workspace.currentChanged.connect(self._on_changed_context)
        self._layout.addWidget(self._workspace)

        # Define Sub-Tabs within Flight space e.g. Plot, Transform, Maps
        self._plot_tab = PlotTab(flight, "Plot", 3)

        self._transform_tab = WorkspaceWidget("Transforms")
        self._map_tab = WorkspaceWidget("Map")

        self._workspace.addTab(self._plot_tab, "Plot")
        self._workspace.addTab(self._transform_tab, "Transforms")
        self._workspace.addTab(self._map_tab, "Map")

        self._context_models = {}

        self._workspace.setCurrentIndex(0)
        self._plot_tab.update()

    def _init_transform_tab(self):
        pass

    def _init_map_tab(self):
        pass

    def _on_changed_context(self, index: int):
        self.log.debug("Flight {} sub-tab changed to index: {}".format(
            self.flight.name, index))
        model = self._workspace.currentWidget().model
        self.contextChanged.emit(model)

    def new_data(self, dsrc: types.DataSource):
        for tab in [self._plot_tab, self._transform_tab, self._map_tab]:
            print("Updating tabs")
            tab.data_modified('add', 'test')

    @property
    def flight(self):
        return self._flight

    @property
    def plot(self):
        return self._plot

    @property
    def context_model(self):
        """Return the QAbstractModel type for the given context i.e. current
        sub-tab of this flight. This enables different sub-tabs of a this
        Flight Tab to specify a tree view model to be displayed as the tabs
        are switched."""
        current_tab = self._workspace.currentWidget()  # type: WorkspaceWidget
        return current_tab.model
