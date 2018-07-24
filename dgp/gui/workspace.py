# -*- coding: utf-8 -*-

import logging

from PyQt5.QtGui import QContextMenuEvent
from PyQt5.QtCore import Qt, pyqtSignal, pyqtBoundSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui

from dgp.core.controllers.controller_interfaces import IBaseController
from dgp.core.controllers.flight_controller import FlightController
from dgp.core.oid import OID
from .workspaces import *


class WorkspaceTab(QWidget):
    """Top Level Tab created for each Flight object open in the workspace"""

    def __init__(self, flight: FlightController, parent=None, flags=0, **kwargs):
        super().__init__(parent=parent, flags=Qt.Widget)
        self.log = logging.getLogger(__name__)
        self._root: IBaseController = flight

        self._layout = QVBoxLayout(self)
        self._setup_tasktabs()

    def _setup_tasktabs(self):
        # Define Sub-Tabs within Flight space e.g. Plot, Transform, Maps
        self._tasktabs = QTabWidget()
        self._tasktabs.setTabPosition(QTabWidget.West)
        self._layout.addWidget(self._tasktabs)

        self._plot_tab = PlotTab(label="Plot", flight=self._root)
        self._tasktabs.addTab(self._plot_tab, "Plot")

        self._transform_tab = TransformTab("Transforms", self._root)
        self._tasktabs.addTab(self._transform_tab, "Transforms")

        # self._line_proc_tab = LineProcessTab("Line Processing", flight)
        # self._tasktabs.addTab(self._line_proc_tab, "Line Processing")

        self._tasktabs.setCurrentIndex(0)
        self._plot_tab.update()

    @property
    def uid(self) -> OID:
        """Return the underlying Flight's UID"""
        return self._root.uid

    @property
    def root(self) -> IBaseController:
        return self._root

    @property
    def plot(self):
        return self._plot


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
