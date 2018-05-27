# coding: utf-8

import logging
import functools

import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QAction, QMenu, QTreeView

from dgp.lib import types
from dgp.gui.models import ProjectModel
from dgp.gui.dialogs import PropertiesDialog


class ProjectTreeView(QTreeView):
    item_removed = pyqtSignal(types.BaseTreeItem)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._project = None
        self.log = logging.getLogger(__name__)

        self.setMinimumSize(QtCore.QSize(0, 300))
        self.setAlternatingRowColors(False)
        self.setAutoExpandDelay(1)
        self.setExpandsOnDoubleClick(False)
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)
        self.setHeaderHidden(True)
        self.setObjectName('project_tree')
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

    def set_project(self, project):
        self._project = project
        self._init_model()

    def _init_model(self):
        """Initialize a new-style ProjectModel from models.py"""
        model = ProjectModel(self._project, parent=self)
        self.setModel(model)
        self.expandAll()

    def toggle_expand(self, index):
        self.setExpanded(index, (not self.isExpanded(index)))

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent, *args, **kwargs):
        # get the index of the item under the click event
        context_ind = self.indexAt(event.pos())
        context_focus = self.model().itemFromIndex(context_ind)

        info_slot = functools.partial(self._info_action, context_focus)
        plot_slot = functools.partial(self._plot_action, context_focus)
        menu = QMenu()
        info_action = QAction("Properties")
        info_action.triggered.connect(info_slot)
        plot_action = QAction("Plot in new window")
        plot_action.triggered.connect(plot_slot)
        if isinstance(context_focus, types.DataSource):
            data_action = QAction("Set Active Data File")
            # TODO: Work on this later, it breaks plotter currently
            # data_action.triggered.connect(
            #     lambda item: context_focus.__setattr__('active', True)
            # )
            menu.addAction(data_action)
            data_delete = QAction("Delete Data File")
            data_delete.triggered.connect(
                lambda: self._remove_data_action(context_focus))
            menu.addAction(data_delete)

        menu.addAction(info_action)
        menu.addAction(plot_action)
        menu.exec_(event.globalPos())
        event.accept()

    def _plot_action(self, item):
        return

    def _info_action(self, item):
        dlg = PropertiesDialog(item, parent=self)
        dlg.exec_()

    def _remove_data_action(self, item: types.BaseTreeItem):
        if not isinstance(item, types.DataSource):
            return
        self.log.warning("Remove data not yet implemented (bugs to fix)")
        return

        raise NotImplementedError("Remove data not yet implemented.")
        # Confirmation Dialog
        confirm = QtWidgets.QMessageBox(parent=self.parent())
        confirm.setStandardButtons(QtWidgets.QMessageBox.Ok)
        confirm.setText("Are you sure you wish to delete: {}".format(item.filename))
        confirm.setIcon(QtWidgets.QMessageBox.Question)
        confirm.setWindowTitle("Confirm Delete")
        res = confirm.exec_()
        if res:
            self.item_removed.emit(item)
            try:
                item.flight.remove_data(item)
            except:
                self.log.exception("Exception occured removing item from flight")

