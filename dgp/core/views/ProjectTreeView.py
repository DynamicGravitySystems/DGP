# -*- coding: utf-8 -*-
from typing import Optional, Tuple, Any, List

from PyQt5 import QtCore
from PyQt5.QtCore import QObject
from PyQt5.QtGui import QContextMenuEvent
from PyQt5.QtWidgets import QTreeView, QMenu, QAction


# from core.controllers.ContextMixin import ContextEnabled
from core.controllers.ProjectController import ProjectController


class ProjectTreeView(QTreeView):
    def __init__(self, parent: Optional[QObject]=None):
        super().__init__(parent=parent)
        print("Initializing ProjectTreeView")
        self.setMinimumSize(QtCore.QSize(0, 300))
        self.setAlternatingRowColors(False)
        self.setAutoExpandDelay(1)
        self.setExpandsOnDoubleClick(True)
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)
        self.setHeaderHidden(True)
        self.setObjectName('project_tree_view')
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self._menu = QMenu(self)
        self._action_refs = []

    def _build_menu(self, bindings: List[Tuple[str, Tuple[Any]]]):
        self._action_refs.clear()
        for attr, params in bindings:
            if hasattr(QMenu, attr):
                res = getattr(self._menu, attr)(*params)
                self._action_refs.append(res)

    def _get_item_attr(self, item, attr):
        return getattr(item, attr, lambda *x, **y: None)

    def contextMenuEvent(self, event: QContextMenuEvent, *args, **kwargs):
        event_index = self.indexAt(event.pos())
        event_item = self.model().itemFromIndex(event_index)

        self._menu.clear()
        bindings = getattr(event_item, 'menu_bindings', [])[:]  # type: List

        if isinstance(event_item, ProjectController) or issubclass(event_item.__class__, ProjectController):
            bindings.insert(0, ('addAction', ("Expand All", self.expandAll)))

        expanded = self.isExpanded(event_index)
        bindings.append(('addAction', ("Expand" if not expanded else "Collapse",
                                       lambda: self.setExpanded(event_index, not expanded))))
        bindings.append(('addAction', ("Properties", self._get_item_attr(event_item, 'properties'))))

        self._build_menu(bindings)
        self._menu.exec_(event.globalPos())
        event.accept()

