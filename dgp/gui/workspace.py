# -*- coding: utf-8 -*-

import logging

from PyQt5.QtGui import QContextMenuEvent, QKeySequence
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QAction
import PyQt5.QtWidgets as QtWidgets

from dgp.core.controllers.controller_interfaces import IBaseController
from dgp.core.controllers.flight_controller import FlightController
from dgp.core.oid import OID
from .workspaces import PlotTab
from .workspaces import TransformTab


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

        self._tasktabs.setCurrentIndex(0)
        self._plot_tab.update()

    @property
    def uid(self) -> OID:
        """Return the underlying Flight's UID"""
        return self._root.uid

    @property
    def root(self) -> IBaseController:
        return self._root


class _WorkspaceTabBar(QtWidgets.QTabBar):
    """Custom Tab Bar to allow us to implement a custom Context Menu to
    handle right-click events."""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setShape(self.RoundedNorth)
        self.setTabsClosable(True)
        self.setMovable(True)

        key_close_action = QAction("Close")
        key_close_action.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_W))
        key_close_action.triggered.connect(
            lambda: self.tabCloseRequested.emit(self.currentIndex()))

        tab_right_action = QAction("TabRight")
        tab_right_action.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_Tab))
        tab_right_action.triggered.connect(self._tab_right)

        tab_left_action = QAction("TabLeft")
        tab_left_action.setShortcut(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_Tab))
        tab_left_action.triggered.connect(self._tab_left)

        self._actions = [key_close_action, tab_right_action, tab_left_action]
        for action in self._actions:
            self.addAction(action)

    def contextMenuEvent(self, event: QContextMenuEvent, *args, **kwargs):
        tab = self.tabAt(event.pos())

        menu = QtWidgets.QMenu()
        menu.setTitle('Tab: ')
        close_action = QAction("Close")
        close_action.triggered.connect(lambda: self.tabCloseRequested.emit(tab))

        menu.addAction(close_action)

        menu.exec_(event.globalPos())
        event.accept()

    def _tab_right(self, *args):
        index = self.currentIndex() + 1
        if index > self.count() - 1:
            index = 0
        self.setCurrentIndex(index)

    def _tab_left(self, *args):
        index = self.currentIndex() - 1
        if index < 0:
            index = self.count() - 1
        self.setCurrentIndex(index)


class MainWorkspace(QtWidgets.QTabWidget):
    """Custom QTabWidget promoted in main_window.ui supporting a custom
    TabBar which enables the attachment of custom event actions e.g. right
    click context-menus for the tab bar buttons."""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTabBar(_WorkspaceTabBar())
        self.tabCloseRequested.connect(self.removeTab)

    def widget(self, index: int) -> WorkspaceTab:
        return super().widget(index)

    # Utility functions for referencing Tab widgets by OID

    def get_tab(self, uid: OID):
        for i in range(self.count()):
            tab = self.widget(i)
            if tab.uid == uid:
                return tab

    def get_tab_index(self, uid: OID):
        for i in range(self.count()):
            if uid == self.widget(i).uid:
                return i

    def close_tab(self, uid: OID):
        index = self.get_tab_index(uid)
        if index is not None:
            self.removeTab(index)

