# -*- coding: utf-8 -*-
import logging
import itertools
from functools import partial
from typing import List, Dict, Tuple
from weakref import WeakValueDictionary

from PyQt5.QtCore import Qt, pyqtSignal, QModelIndex, QAbstractItemModel, QSize, QPoint
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QMouseEvent, QColor, QPalette
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QListView, QMenu, QAction,
                             QSizePolicy, QStyledItemDelegate,
                             QStyleOptionViewItem, QHBoxLayout, QLabel,
                             QColorDialog, QToolButton, QFrame, QComboBox)
from pandas import Series
from pyqtgraph import PlotDataItem

from dgp.core import Icon, OID
from dgp.gui.plotting.backends import GridPlotWidget, Axis, LINE_COLORS

__all__ = ['ChannelController', 'ChannelItem']
_log = logging.getLogger(__name__)


class ColorPicker(QLabel):
    """ColorPicker creates a colored label displaying its current color value

    Clicking on the picker launches a QColorDialog, allowing the user to choose
    a color.

    Parameters
    ----------
    color : QColor, optional
        Specify the initial color value of the color picker
    parent : QWidget, optional

    """
    sigColorChanged = pyqtSignal(object)

    def __init__(self, color: QColor = QColor(), parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred))
        self.setToolTip("Customize channel line color")
        self._color = color
        self._update()

    @property
    def color(self) -> QColor:
        return self._color

    def mouseReleaseEvent(self, event: QMouseEvent):
        color: QColor = QColorDialog.getColor(self._color, parent=self)
        if color.isValid():
            self._color = color
            self.sigColorChanged.emit(self._color)
            self._update()

    def sizeHint(self):
        return QSize(30, 30)

    def _update(self):
        """Updates the background color for display"""
        palette: QPalette = self.palette()
        palette.setColor(self.backgroundRole(), self._color)
        self.setPalette(palette)


class DataChannelEditor(QFrame):
    """This object defines the widget displayed when a data channel is selected
    within the ChannelController listr view.

    This widget provides controls enabling a user to select which plot and axis
    a channel is plotted on, and to set the visibility and color of the channel.

    """
    SIZE = QSize(140, 35)

    def __init__(self, item: 'ChannelItem', rows=1, parent=None):
        super().__init__(parent, flags=Qt.Widget)
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)
        self.setAutoFillBackground(True)

        self._item = item

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)
        sp_btn = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        sp_combo = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)

        self._label = QLabel(item.name)
        self._picker = ColorPicker(color=item.line_color, parent=self)
        self._picker.sigColorChanged.connect(item.set_color)

        # Plot Row Selection ComboBox

        self._row_cb = QComboBox()
        self._row_cb.setToolTip("Plot channel on selected row")
        self._row_cb.setSizePolicy(sp_combo)
        for i in range(rows):
            self._row_cb.addItem(str(i), i)
        self._row_cb.setCurrentIndex(item.target_row)
        self._row_cb.currentIndexChanged.connect(self.change_row)

        # Left/Right Axis Controls
        self._left = QToolButton()
        self._left.setCheckable(False)
        self._left.setToolTip("Plot channel on left y-axis")
        self._left.setIcon(Icon.ARROW_LEFT.icon())
        self._left.setSizePolicy(sp_btn)
        self._left.clicked.connect(partial(self.change_axis, Axis.LEFT))
        self._right = QToolButton()
        self._right.setCheckable(False)
        self._right.setToolTip("Plot channel on right y-axis")
        self._right.setIcon(Icon.ARROW_RIGHT.icon())
        self._right.setSizePolicy(sp_btn)
        self._right.clicked.connect(partial(self.change_axis, Axis.RIGHT))

        # Channel Settings ToolButton
        self._settings = QToolButton()
        self._settings.setSizePolicy(sp_btn)
        self._settings.setIcon(Icon.SETTINGS.icon())

        layout.addWidget(self._label)
        layout.addSpacing(5)
        layout.addWidget(self._picker)
        layout.addSpacing(2)
        layout.addWidget(self._row_cb)
        layout.addSpacing(5)
        layout.addWidget(self._left)
        layout.addWidget(self._right)
        layout.addWidget(self._settings)

    def toggle_axis(self, axis: Axis, checked: bool):
        pass

    def change_axis(self, axis):

        self._item.set_axis(axis, emit=False)
        if self._item.checkState() == Qt.Checked:
            self._item.update()
        else:
            self._item.setCheckState(Qt.Checked)

    def change_row(self, index):
        row: int = self._row_cb.currentData(Qt.UserRole)
        self._item.set_row(row)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self._item.setCheckState(Qt.Unchecked if self._item.visible else Qt.Checked)


class ChannelDelegate(QStyledItemDelegate):
    def __init__(self, rows=1, parent=None):
        super().__init__(parent=parent)
        self._rows = rows

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem,
                     index: QModelIndex):
        item = index.model().itemFromIndex(index)
        editor = DataChannelEditor(item, self._rows, parent)

        return editor

    def setModelData(self, editor: QWidget, model: QAbstractItemModel,
                     index: QModelIndex):
        """Do nothing, editor does not directly mutate model data"""
        pass

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        return DataChannelEditor.SIZE


class ChannelItem(QStandardItem):
    """The ChannelItem defines the UI representation of a plotable data channel

    ChannelItems maintain the desired state of the channel in relation to its
    visibility, line color, plot axis, and plot row/column. It is the
    responsibility of the owning controller to act on state changes of the
    channel item.

    The itemChanged signal is emitted (via the QStandardItemModel owner) by the
    ChannelItem whenever its internal state has been updated.

    Parameters
    ----------
    name: str
        Display name for the channel
    color : QColor, optional
        Optional base color for this channel item

    Notes
    -----
    Setter methods are used instead of property setters in order to facilitate
    signal connections, or setting of properties from within a lambda expression

    """
    _base_color = QColor(Qt.white)

    def __init__(self, name: str, color=QColor()):
        super().__init__()
        self.setCheckable(True)
        self.name = name
        self._row = 0
        self._col = 0
        self._axis = Axis.LEFT
        self._color = color
        self.uid = OID(tag=name)

        self.update(emit=False)

    @property
    def target_row(self):
        return self._row

    def set_row(self, row, emit=True):
        self._row = row
        if emit:
            self.update()

    @property
    def target_axis(self):
        return self._axis

    def set_axis(self, axis: Axis, emit=True):
        self._axis = axis
        if emit:
            self.update()

    @property
    def line_color(self) -> QColor:
        return self._color

    def set_color(self, color: QColor, emit=True):
        self._color = color
        if emit:
            self.update()

    @property
    def visible(self) -> bool:
        return self.checkState() == Qt.Checked

    def set_visible(self, visible: bool, emit=True):
        self.setCheckState(Qt.Checked if visible else Qt.Unchecked)
        if emit:
            self.update()

    def update(self, emit=True):
        if self.visible:
            self.setText(f'{self.name} - {self.target_row} | {self.target_axis.value}')
            self.setBackground(self.line_color)
        else:
            self.setText(f'{self.name}')
            self.setBackground(self._base_color)
        if emit:
            self.emitDataChanged()

    def key(self) -> Tuple[int, int, Axis]:
        return self._row, self._col, self._axis

    def __hash__(self):
        return hash(self.uid)


class ChannelController(QWidget):
    """The ChannelController widget is associated with a Plotter, e.g. a
    :class:`GridPlotWidget`, and provides an interface for a user to select and
    plot any of the various :class:`pandas.Series` objects supplied to it.

    Parameters
    ----------
    plotter : :class:`~dgp.gui.plotting.backends.GridPlotWidget`
    *series : :class:`pandas.Series`
    binary_series : List of :class:`pandas.Series`, optional
        Optional list of series to be interpreted/grouped as binary data, e.g.
        for status bits
    parent : QWidget, optional

    """
    def __init__(self, plotter: GridPlotWidget, *series: Series,
                 binary_series: List[Series] = None, parent: QWidget = None):
        super().__init__(parent, flags=Qt.Widget)
        self.plotter = plotter
        self.plotter.sigPlotCleared.connect(self._channels_cleared)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred))
        self._layout = QVBoxLayout(self)

        self._model = QStandardItemModel()
        self._model.itemChanged.connect(self.channel_changed)
        self._binary_model = QStandardItemModel()
        self._binary_model.itemChanged.connect(self.binary_changed)

        self._series: Dict[OID, Series] = {}
        self._active: Dict[OID, PlotDataItem] = WeakValueDictionary()
        self._indexes: Dict[OID, Tuple[int, int, Axis]] = {}

        self._colors = itertools.cycle(LINE_COLORS)

        # Define/configure List Views
        series_delegate = ChannelDelegate(rows=self.plotter.rows, parent=self)
        self.series_view = QListView(parent=self)
        self.series_view.setMinimumWidth(250)
        self.series_view.setUniformItemSizes(True)
        self.series_view.setEditTriggers(QListView.SelectedClicked |
                                         QListView.DoubleClicked |
                                         QListView.CurrentChanged)
        self.series_view.setItemDelegate(series_delegate)
        self.series_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.series_view.customContextMenuRequested.connect(self._context_menu)
        self.series_view.setModel(self._model)

        self._layout.addWidget(self.series_view, stretch=2)

        self.binary_view = QListView(parent=self)
        self.binary_view.setEditTriggers(QListView.NoEditTriggers)
        self.binary_view.setUniformItemSizes(True)
        self.binary_view.setModel(self._binary_model)

        self._status_label = QLabel("Status Channels")
        self._layout.addWidget(self._status_label, alignment=Qt.AlignHCenter)

        self._layout.addWidget(self.binary_view, stretch=1)

        self.set_series(*series)
        binary_series = binary_series or []
        self.set_binary_series(*binary_series)

    def set_series(self, *series, clear=True):
        if clear:
            self._model.clear()

        for s in series:
            item = ChannelItem(s.name, QColor(next(self._colors)))
            self._series[item.uid] = s
            self._model.appendRow(item)

    def set_binary_series(self, *series, clear=True):
        if clear:
            self._binary_model.clear()

        for b in series:
            item = QStandardItem(b.name)
            item.uid = OID()
            item.setCheckable(True)
            self._series[item.uid] = b
            self._binary_model.appendRow(item)

    def get_state(self):
        active_state = {}
        for uid, item in self._active.items():
            row, col, axis = self._indexes[uid]
            active_state[item.name()] = row, col, axis.value
        return active_state

    def restore_state(self, state: Dict[str, Tuple[int, int, str]]):
        for i in range(self._model.rowCount()):
            item: ChannelItem = self._model.item(i, 0)
            if item.name in state:
                key = state[item.name]
                item.set_visible(True, emit=False)
                item.set_row(key[0], emit=False)
                item.set_axis(Axis(key[2]), emit=True)

        for i in range(self._binary_model.rowCount()):
            item: QStandardItem = self._binary_model.item(i, 0)
            if item.text() in state:
                item.setCheckState(Qt.Checked)

    def channel_changed(self, item: ChannelItem):
        item.update(emit=False)
        if item.uid in self._active:  # Channel is already somewhere on the plot
            if not item.visible:
                self._remove_series(item)
            else:
                self._update_series(item)

        elif item.visible:  # Channel is not yet plotted
            self._add_series(item)
            series = self._series[item.uid]
            line = self.plotter.add_series(series, item.target_row,
                                           axis=item.target_axis)
            self._active[item.uid] = line
        else:  # Item is not active, and its state is not visible (do nothing)
            pass

    def _add_series(self, item: ChannelItem):
        """Add a new series to the controls plotter"""
        series = self._series[item.uid]
        row = item.target_row
        axis = item.target_axis

        line = self.plotter.add_series(series, row, col=0, axis=axis,
                                       pen=item.line_color)
        self._active[item.uid] = line
        self._indexes[item.uid] = item.key()

    def _update_series(self, item: ChannelItem):
        """Update paramters (color, axis, row) of an already plotted series"""
        line = self._active[item.uid]
        line.setPen(item.line_color)

        # Need to know the current axis and row of an _active line
        if item.key() != self._indexes[item.uid]:
            self._remove_series(item)
            self._add_series(item)

    def _remove_series(self, item: ChannelItem):
        line = self._active[item.uid]
        self.plotter.remove_plotitem(line)
        try:
            del self._indexes[item.uid]
        except KeyError:
            pass

    def _channels_cleared(self):
        """Respond to plot notification that all lines have been cleared"""
        _log.debug("Plot channels cleared")
        for i in range(self._model.rowCount()):
            item: ChannelItem = self._model.item(i)
            item.set_visible(False, emit=False)
            item.update(emit=False)
        for i in range(self._binary_model.rowCount()):
            item: QStandardItem = self._binary_model.item(i)
            item.setCheckState(Qt.Unchecked)

    def binary_changed(self, item: QStandardItem):
        if item.checkState() == Qt.Checked:
            if item.uid in self._active:
                return
            else:
                series = self._series[item.uid]
                line = self.plotter.add_series(series, 1, 0, axis=Axis.RIGHT)
                self._active[item.uid] = line
                self._indexes[item.uid] = 1, 0, Axis.RIGHT
        else:
            try:
                line = self._active[item.uid]
                self.plotter.remove_plotitem(line)
            except KeyError:
                # Item may have already been deleted by the plot
                pass

    def _context_menu(self, point: QPoint):
        index: QModelIndex = self.series_view.indexAt(point)
        if not index.isValid():
            # DEBUG
            print("Providing general context menu (clear items)")
        else:
            # DEBUG
            print(f'Providing menu for item {self._model.itemFromIndex(index).text()}')
