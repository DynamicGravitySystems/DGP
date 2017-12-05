# coding: utf-8

# Class for custom Qt Widgets

import logging

from PyQt5.QtGui import (QDropEvent, QDragEnterEvent, QDragMoveEvent,
                         QContextMenuEvent)
from PyQt5.QtCore import QMimeData, Qt, pyqtSignal, pyqtBoundSignal
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QTabWidget,
                             QTreeView, QStackedWidget, QSizePolicy)
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui


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
    def __init__(self, flight: Flight, label: str, axes: int, **kwargs):
        super().__init__(label, **kwargs)
        self.log = logging.getLogger('PlotTab')

        vlayout = QVBoxLayout()
        self._plot = LineGrabPlot(flight, axes)
        self._plot.line_changed.connect(self._on_modified_line)
        self._flight = flight

        vlayout.addWidget(self._plot)
        vlayout.addWidget(self._plot.get_toolbar())
        self.setLayout(vlayout)
        self._apply_state()
        self._init_model()

    def _apply_state(self) -> None:
        """
        Apply saved state to plot based on Flight plot channels.
        """
        state = self._flight.get_plot_state()
        draw = False
        for dc in state:
            self._plot.add_series(dc, dc.plotted)

        for line in self._flight.lines:
            self._plot.add_patch(line.start, line.stop, line.uid,
                                 label=line.label)
            draw = True
        if draw:
            self._plot.draw()

    def _init_model(self):
        channels = self._flight.channels
        plot_model = models.ChannelListModel(channels, len(self._plot))
        plot_model.plotOverflow.connect(self._too_many_children)
        plot_model.channelChanged.connect(self._on_channel_changed)
        plot_model.update()
        self.model = plot_model

    def data_modified(self, action: str, uid: str):
        self.log.info("Adding channels to model.")
        channels = self._flight.channels
        self.model.set_channels(channels)

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

    def _on_channel_changed(self, new: int, channel: types.DataChannel):
        self.log.info("Channel change request: new index: {}".format(new))

        self.log.debug("Moving series on plot")
        self._plot.remove_series(channel)
        if new != -1:
            self._plot.add_series(channel, new)
        else:
            print("destination is -1")
        self.model.update()

    def _too_many_children(self, uid):
        self.log.warning("Too many children for plot: {}".format(uid))


class TransformTab(WorkspaceWidget):
    def __init__(self, flight, label, *args, **kwargs):
        super().__init__(label)
        self._flight = flight
        self._elements = {}

        self._setupUi()
        self._init_model()

    def _setupUi(self) -> None:
        """
        Initialize the UI Components of the Transform Tab.
        Major components (plot, transform view, info panel) are added to the
        instance _elements dict.

        """
        grid = QGridLayout()
        transform = QTreeView()
        transform.setSizePolicy(QSizePolicy.Minimum,
                                       QSizePolicy.Expanding)
        info = QtWidgets.QTextEdit()
        info.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        plot = LineGrabPlot(self._flight, 2)
        plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        plot_toolbar = plot.get_toolbar()

        # Testing layout
        btn = QtWidgets.QPushButton("Add")
        btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        btn.pressed.connect(lambda: info.show())

        btn2 = QtWidgets.QPushButton("Remove")
        btn2.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        btn2.pressed.connect(lambda: info.hide())

        grid.addWidget(transform, 0, 0)
        grid.addWidget(btn, 2, 0)
        grid.addWidget(btn2, 3, 0)
        grid.addWidget(info, 1, 0)
        grid.addWidget(plot, 0, 1, 3, 1)
        grid.addWidget(plot_toolbar, 3, 1)

        self.setLayout(grid)

        elements = {'transform': transform,
                    'plot': plot,
                    'toolbar': plot_toolbar,
                    'info': info}
        self._elements.update(elements)

    def _init_model(self):
        channels = self._flight.channels
        plot_model = models.ChannelListModel(channels, len(self._elements[
                                                               'plot']))
        # plot_model.plotOverflow.connect(self._too_many_children)
        # plot_model.channelChanged.connect(self._on_channel_changed)
        plot_model.update()
        self.model = plot_model


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

        # self._transform_tab = WorkspaceWidget("Transforms")
        self._transform_tab = TransformTab(flight, "Transforms")
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


class CustomTabBar(QtWidgets.QTabBar):
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


class TabWorkspace(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        bar = CustomTabBar()
        self.setTabBar(bar)
