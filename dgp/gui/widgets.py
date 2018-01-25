# coding: utf-8

# Class for custom Qt Widgets

import logging

from PyQt5.QtGui import (QDropEvent, QDragEnterEvent, QDragMoveEvent,
                         QContextMenuEvent)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtBoundSignal
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QTabWidget, QTreeView, QSizePolicy)
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui
import pyqtgraph as pg
from pyqtgraph.flowchart import Flowchart

import dgp.gui.models as models
import dgp.lib.types as types
from dgp.lib.enums import DataTypes
from .plotter import LineGrabPlot, LineUpdate
from dgp.lib.project import Flight
from dgp.lib.etc import gen_uuid
from dgp.gui.dialogs import ChannelSelectionDialog
from dgp.lib.transform import *


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
    def __init__(self, label: str, flight: Flight, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.label = label
        self._flight = flight
        self._uid = gen_uuid('ww')
        self._plot = None

    def widget(self):
        return None

    @property
    def flight(self) -> Flight:
        return self._flight
    
    @property
    def plot(self) -> LineGrabPlot:
        return self._plot

    @plot.setter
    def plot(self, value):
        self._plot = value

    def data_modified(self, action: str, dsrc: types.DataSource):
        pass

    @property
    def uid(self):
        return self._uid


class PlotTab(WorkspaceWidget):
    """Sub-tab displayed within Flight tab interface. Displays canvas for
    plotting data series."""
    defaults = {'gravity': 0, 'long': 1, 'cross': 1}

    def __init__(self, label: str, flight: Flight, axes: int,
                 plot_default=True, **kwargs):
        super().__init__(label, flight, **kwargs)
        self.log = logging.getLogger('PlotTab')
        self.model = None
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

        self._enter_line_selection = QtWidgets.QPushButton("Enter Line "
                                                           "Selection Mode")
        top_button_hlayout.addWidget(self._enter_line_selection,
                                     alignment=Qt.AlignRight)
        vlayout.addLayout(top_button_hlayout)

        self.plot = LineGrabPlot(self.flight, self._axes_count)
        for line in self.flight.lines:
            self.plot.add_patch(line.start, line.stop, line.uid, line.label)
        self.plot.line_changed.connect(self._on_modified_line)

        vlayout.addWidget(self.plot)
        vlayout.addWidget(self.plot.get_toolbar(), alignment=Qt.AlignBottom)
        self.setLayout(vlayout)

    def _init_model(self, default_state=False):
        channels = self.flight.channels
        plot_model = models.ChannelListModel(channels, len(self.plot))
        plot_model.plotOverflow.connect(self._too_many_children)
        plot_model.channelChanged.connect(self._on_channel_changed)
        self.model = plot_model

        if default_state:
            self.set_defaults(channels)

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
                           "stop={stop}, label={label}"
                           .format(flt=self.flight.name, start=info.start,
                                   stop=info.stop, label=info.label))

    def _on_channel_changed(self, new: int, channel: types.DataChannel):
        self.plot.remove_series(channel)
        if new != -1:
            try:
                self.plot.add_series(channel, new)
            except:
                self.log.exception("Error adding series to plot")
        self.model.update()

    def _too_many_children(self, uid):
        self.log.warning("Too many children for plot: {}".format(uid))


class TransformTab(WorkspaceWidget):
    def __init__(self, label: str, flight: Flight):
        super().__init__(label, flight)
        self._layout = QGridLayout()
        self.setLayout(self._layout)

        self.fc = None
        self.plots = []
        self._init_flowchart()
        self.populate_flowchart()

    def _init_flowchart(self):
        fc_terminals = {"Gravity": dict(io='in'),
                        "Trajectory": dict(io='in'),
                        "Output": dict(io='out')}
        fc = Flowchart(library=LIBRARY, terminals=fc_terminals)
        fc_ctrl_widget = fc.widget()
        chart_window = fc_ctrl_widget.cwWin
        # Force the Flowchart pop-out window to close when the main app exits
        chart_window.setAttribute(Qt.WA_QuitOnClose, False)

        fc_ctrl_widget.ui.reloadBtn.setEnabled(False)
        self._layout.addWidget(fc_ctrl_widget, 0, 0, 2, 1)

        plot_1 = pg.PlotWidget()
        self._layout.addWidget(plot_1, 0, 1)
        plot_2 = pg.PlotWidget()
        self._layout.addWidget(plot_2, 1, 1)
        plot_list = {'Top Plot': plot_1, 'Bottom Plot': plot_2}

        plotnode_1 = fc.createNode('PlotWidget', pos=(0, -150))
        plotnode_1.setPlotList(plot_list)
        plotnode_1.setPlot(plot_1)
        plotnode_2 = fc.createNode('PlotWidget', pos=(150, -150))
        plotnode_2.setPlotList(plot_list)
        plotnode_2.setPlot(plot_2)

        self.plots.append(plotnode_1)
        self.plots.append(plotnode_2)
        self.fc = fc

    def populate_flowchart(self):
        """Populate the flowchart/Transform interface with a default
        'example'/base network of Nodes dependent on available data."""
        if self.fc is None:
            return
        else:
            fc = self.fc
        grav = self.flight.get_source(DataTypes.GRAVITY)
        gps = self.flight.get_source(DataTypes.TRAJECTORY)
        if grav is not None:
            fc.setInput(Gravity=grav.load())
            demux = LIBRARY.getNodeType('LineDemux')('Demux', self.flight)
            fc.addNode(demux, 'Demux')

        if gps is not None:
            fc.setInput(Trajectory=gps.load())
            eotvos = fc.createNode('Eotvos', pos=(0, 0))
            fc.connectTerminals(fc['Trajectory'], eotvos['data_in'])
            fc.connectTerminals(eotvos['data_out'], self.plots[0]['In'])

    def data_modified(self, action: str, dsrc: types.DataSource):
        """Slot: Called when a DataSource has been added/removed from the
        Flight this tab/workspace is associated with."""
        if action.lower() == 'add':
            if dsrc.dtype == DataTypes.TRAJECTORY:
                self.fc.setInput(Trajectory=dsrc.load())
            elif dsrc.dtype == DataTypes.GRAVITY:
                self.fc.setInput(Gravity=dsrc.load())


class MapTab(WorkspaceWidget):
    pass


class FlightTab(QWidget):
    """Top Level Tab created for each Flight object open in the workspace"""

    contextChanged = pyqtSignal(models.BaseTreeModel)  # type: pyqtBoundSignal

    def __init__(self, flight: Flight, parent=None, flags=0, **kwargs):
        super().__init__(parent=parent, flags=Qt.Widget)
        self.log = logging.getLogger(__name__)
        self._flight = flight

        self._layout = QVBoxLayout(self)
        # _workspace is the inner QTabWidget containing the WorkspaceWidgets
        self._workspace = QTabWidget()
        self._workspace.setTabPosition(QTabWidget.West)
        self._workspace.currentChanged.connect(self._on_changed_context)
        self._layout.addWidget(self._workspace)

        # Define Sub-Tabs within Flight space e.g. Plot, Transform, Maps
        self._plot_tab = PlotTab(label="Plot", flight=flight, axes=3)
        self._workspace.addTab(self._plot_tab, "Plot")

        self._transform_tab = TransformTab("Transforms", flight)
        self._workspace.addTab(self._transform_tab, "Transforms")

        # self._map_tab = WorkspaceWidget("Map")
        # self._workspace.addTab(self._map_tab, "Map")

        self._context_models = {}

        self._workspace.setCurrentIndex(0)
        self._plot_tab.update()

    def subtab_widget(self):
        return self._workspace.currentWidget().widget()

    def _on_changed_context(self, index: int):
        self.log.debug("Flight {} sub-tab changed to index: {}".format(
            self.flight.name, index))
        try:
            model = self._workspace.currentWidget().model
            self.contextChanged.emit(model)
        except AttributeError:
            pass

    def new_data(self, dsrc: types.DataSource):
        for tab in [self._plot_tab, self._transform_tab]:
            tab.data_modified('add', dsrc)

    def data_deleted(self, dsrc):
        for tab in [self._plot_tab]:
            print("Calling remove for each tab")
            tab.data_modified('remove', dsrc)

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


class _FlightTabBar(QtWidgets.QTabBar):
    """Custom Tab Bar to allow us to implement a custom Context Menu to
    handle right-click events."""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setShape(self.RoundedNorth)
        self.setTabsClosable(True)
        self.setMovable(True)

        self._actions = []  # Store action objects to keep a reference so no GC
        # Allow closing tab via Ctrl+W key shortcut
        _close_action = QtWidgets.QAction("Close")
        _close_action.triggered.connect(
            lambda: self.tabCloseRequested.emit(self.currentIndex()))
        _close_action.setShortcut(QtGui.QKeySequence("Ctrl+W"))
        self.addAction(_close_action)
        self._actions.append(_close_action)

    def contextMenuEvent(self, event: QContextMenuEvent, *args, **kwargs):
        tab = self.tabAt(event.pos())

        menu = QtWidgets.QMenu()
        menu.setTitle('Tab: ')
        kill_action = QtWidgets.QAction("Kill")
        kill_action.triggered.connect(lambda: self.tabCloseRequested.emit(tab))

        menu.addAction(kill_action)

        menu.exec_(event.globalPos())
        event.accept()


class FlightWorkspace(QtWidgets.QTabWidget):
    """Custom QTabWidget promoted in main_window.ui supporting a custom
    TabBar which enables the attachment of custom event actions e.g. right
    click context-menus for the tab bar buttons."""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTabBar(_FlightTabBar())
