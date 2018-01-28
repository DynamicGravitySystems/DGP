# coding: utf-8


import logging

from PyQt5.QtGui import QContextMenuEvent
from PyQt5.QtCore import Qt, pyqtSignal, pyqtBoundSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui


from .workspaces import *
import dgp.gui.models as models
import dgp.lib.types as types
from dgp.lib.project import Flight


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

        self._line_proc_tab = LineProcessTab("Line Processing", flight)
        self._workspace.addTab(self._line_proc_tab, "Line Processing")

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


class _WorkspaceTabBar(QtWidgets.QTabBar):
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


class MainWorkspace(QtWidgets.QTabWidget):
    """Custom QTabWidget promoted in main_window.ui supporting a custom
    TabBar which enables the attachment of custom event actions e.g. right
    click context-menus for the tab bar buttons."""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTabBar(_WorkspaceTabBar())
