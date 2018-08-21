# -*- coding: utf-8 -*-
import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtGui import QContextMenuEvent, QKeySequence
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction

from dgp.core.oid import OID
from ..workspaces.base import WorkspaceTab


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


class WorkspaceWidget(QtWidgets.QTabWidget):
    """Custom QTabWidget promoted in main_window.ui supporting a custom
    TabBar which enables the attachment of custom event actions e.g. right
    click context-menus for the tab bar buttons.

    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTabBar(_WorkspaceTabBar())
        self.tabCloseRequested.connect(self.close_tab_by_index)

    def widget(self, index: int) -> WorkspaceTab:
        return super().widget(index)

    def addTab(self, tab: WorkspaceTab, label: str = None):
        if label is None:
            label = tab.title
        super().addTab(tab, label)
        self.setCurrentWidget(tab)

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

    def close_tab_by_index(self, index: int):
        tab = self.widget(index)
        tab.close()
        self.removeTab(index)

    def close_tab(self, uid: OID):
        tab = self.get_tab(uid)
        if tab is not None:
            tab.close()
        index = self.get_tab_index(uid)
        if index is not None:
            self.removeTab(index)
