# -*- coding: utf-8 -*-
import functools
from typing import Union

from PyQt5.QtCore import QObject, Qt, pyqtSignal, QModelIndex, QIdentityProxyModel
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QContextMenuEvent
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QListView, QMenu, QAction,
                             QSizePolicy, QPushButton)


class ChannelProxyModel(QIdentityProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def setSourceModel(self, model: QStandardItemModel):
        super().setSourceModel(model)

    def insertColumns(self, p_int, p_int_1, parent=None, *args, **kwargs):
        pass


class ChannelListView(QListView):
    channel_plotted = pyqtSignal(int, QStandardItem)
    channel_unplotted = pyqtSignal(QStandardItem)

    def __init__(self, nplots=1, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.MinimumExpanding))
        self.setEditTriggers(QListView.NoEditTriggers)
        self._n = nplots
        self._actions = []

    def setModel(self, model: QStandardItemModel):
        super().setModel(model)

    def contextMenuEvent(self, event: QContextMenuEvent, *args, **kwargs):
        index: QModelIndex = self.indexAt(event.pos())
        self._actions.clear()
        item = self.model().itemFromIndex(index)
        menu = QMenu(self)
        for i in range(self._n):
            action: QAction = QAction("Plot on %d" % i)
            action.triggered.connect(functools.partial(self._plot_item, i, item))
            # action.setCheckable(True)
            # action.setChecked(item.checkState())
            # action.toggled.connect(functools.partial(self._channel_toggled, item, i))
            self._actions.append(action)
            menu.addAction(action)

        action_del: QAction = QAction("Clear from plot")
        action_del.triggered.connect(functools.partial(self._unplot_item, item))
        menu.addAction(action_del)

        menu.exec_(event.globalPos())
        event.accept()

    def _channel_toggled(self, item: QStandardItem, plot: int, checked: bool):
        print("item: %s in checkstate %s on plot: %d" % (item.data(Qt.DisplayRole), str(checked), plot))
        item.setCheckState(checked)

    def _plot_item(self, plot: int, item: QStandardItem):
        print("Plotting %s on plot# %d" % (item.data(Qt.DisplayRole), plot))
        self.channel_plotted.emit(plot, item)

    def _unplot_item(self, item: QStandardItem):
        self.channel_unplotted.emit(item)


class ChannelSelectWidget(QWidget):
    """
    Working Notes:
    Lets assume a channel can only be plotted once in total no matter how many plots

    Options - we can use check boxes, right-click context menu, or a table with 3 checkboxes (but 3 copies of the
    channel?)

    Either the channel (QStandardItem) or the view needs to track its plotted state somehow
    Perhaps we can use a QIdentityProxyModel to which we can add columns to without modifying
    the source model.

    """
    channel_added = pyqtSignal(int, QStandardItem)
    channel_removed = pyqtSignal(QStandardItem)
    channels_cleared = pyqtSignal()

    def __init__(self, model: QStandardItemModel, plots: int = 1, parent: Union[QWidget, QObject] = None):
        super().__init__(parent=parent, flags=Qt.Widget)
        self._model = model
        self._model.modelReset.connect(self.channels_cleared.emit)
        self._model.rowsInserted.connect(self._rows_inserted)
        self._model.itemChanged.connect(self._item_changed)

        self._view = ChannelListView(nplots=2, parent=self)
        self._view.channel_plotted.connect(self.channel_added.emit)
        self._view.channel_unplotted.connect(self.channel_removed.emit)
        self._view.setModel(self._model)

        self._qpb_clear = QPushButton("Clear Channels")
        self._qpb_clear.clicked.connect(self.channels_cleared.emit)
        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self._view)
        self._layout.addWidget(self._qpb_clear)


    def _rows_inserted(self, parent: QModelIndex, first: int, last: int):
        pass
        # print("Rows have been inserted: %d to %d" % (first, last))

    def _rows_removed(self, parent: QModelIndex, first: int, last: int):
        pass
        # print("Row has been removed: %d" % first)

    def _model_reset(self):
        print("Model has been reset")

    def _item_changed(self, item: QStandardItem):
        # Work only on single plot for now
        if item.checkState():
            print("Plotting channel: %s" % item.data(Qt.DisplayRole))
            self.channel_added.emit(0, item)
        else:
            print("Removing channel: %s" % item.data(Qt.DisplayRole))
            self.channel_removed.emit(item)
