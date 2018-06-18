# -*- coding: utf-8 -*-

"""
Definitions for task specific plot interfaces.
"""
import logging
from itertools import count
from typing import Dict, Tuple, Union, List

import pandas as pd
import PyQt5.QtCore as QtCore
import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtWidgets import QMenu, QAction
from PyQt5.QtCore import pyqtSignal
from dgp.lib.types import LineUpdate
from dgp.lib.etc import gen_uuid
from .backends import BasePlot, PYQTGRAPH, AbstractSeriesPlotter

import pyqtgraph as pg
from pyqtgraph.graphicsItems.LinearRegionItem import LinearRegionItem
from pyqtgraph.graphicsItems.TextItem import TextItem

_log = logging.getLogger(__name__)


"""
TODO: Many of the classes here are not used, in favor of the PyQtGraph line selection interface.
Consider whether to remove the obsolete code, or keep it around while the new plot interface
matures. There are still some quirks and features missing from the PyQtGraph implementation
that will need to be worked out and properly tested.

"""


class TransformPlot:
    """Plot interface used for displaying transformation results.
    May need to display data plotted against time series or scalar series.
    """
    def __init__(self, rows=2, cols=1, sharex=True, sharey=False, grid=True,
                 parent=None):
        self.widget = BasePlot(backend=PYQTGRAPH, rows=rows, cols=cols,
                               sharex=sharex, sharey=sharey, grid=grid,
                               background='w', parent=parent)

    @property
    def plots(self) -> List[AbstractSeriesPlotter]:
        return self.widget.plots

    def __getattr__(self, item):
        try:
            return getattr(self.widget, item)
        except AttributeError:
            raise AttributeError("Plot Widget has no Attribute: ", item)


class LinearFlightRegion(LinearRegionItem):
    """Custom LinearRegionItem class to provide override methods on various
    click events."""
    def __init__(self, values=(0, 1), orientation=None, brush=None,
                 movable=True, bounds=None, parent=None, label=None):
        super().__init__(values=values, orientation=orientation, brush=brush,
                         movable=movable, bounds=bounds)

        self.parent = parent
        self._grpid = None
        self._label_text = label or ''
        self.label = TextItem(text=self._label_text, color=(0, 0, 0),
                              anchor=(0, 0))
        # self.label.setPos()
        self._menu = QMenu()
        self._menu.addAction(QAction('Remove', self, triggered=self._remove))
        self._menu.addAction(QAction('Set Label', self,
                                     triggered=self._getlabel))
        self.sigRegionChanged.connect(self._move_label)

    def mouseClickEvent(self, ev):
        if not self.parent.selection_mode:
            return
        if ev.button() == QtCore.Qt.RightButton and not self.moving:
            ev.accept()
            pos = ev.screenPos().toPoint()
            pop_point = QtCore.QPoint(pos.x(), pos.y())
            self._menu.popup(pop_point)
            return True
        else:
            return super().mouseClickEvent(ev)

    def _move_label(self, lfr):
        x0, x1 = self.getRegion()

        self.label.setPos(x0, 0)

    def _remove(self):
        try:
            self.parent.remove(self)
        except AttributeError:
            return

    def _getlabel(self):
        text, result = QtWidgets.QInputDialog.getText(None,
                                                      "Enter Label",
                                                      "Line Label:",
                                                      text=self._label_text)
        if not result:
            return
        try:
            self.parent.set_label(self, str(text).strip())
        except AttributeError:
            return

    def set_label(self, text):
        self.label.setText(text)

    @property
    def group(self):
        return self._grpid

    @group.setter
    def group(self, value):
        self._grpid = value




class PqtLineSelectPlot(QtCore.QObject):
    """New prototype Flight Line selection plot using Pyqtgraph as the
    backend.

    This class supports flight-line selection using PyQtGraph LinearRegionItems
    """
    line_changed = pyqtSignal(LineUpdate)

    def __init__(self, flight, rows=3, parent=None):
        super().__init__(parent=parent)
        self.widget = BasePlot(backend=PYQTGRAPH, rows=rows, cols=1,
                               sharex=True, grid=True, background='w',
                               parent=parent)
        self._flight = flight
        self.widget.add_onclick_handler(self.onclick)
        self._lri_id = count(start=1)
        self._selections = {}  # Flight-line 'selection' patches: grpid: group[LinearFlightRegion's]
        self._updating = False  # Class flag for locking during update

        # Rate-limit line updates using a timer.
        self._line_update = None  # type: LinearFlightRegion
        self._update_timer = QtCore.QTimer(self)
        self._update_timer.setInterval(100)
        self._update_timer.timeout.connect(self._update_done)

        self._selecting = False

    def __getattr__(self, item):
        try:
            return getattr(self.widget, item)
        except AttributeError:
            raise AttributeError("Plot Widget has no Attribute: ", item)

    def __len__(self):
        return len(self.widget)

    @property
    def selection_mode(self):
        return self._selecting

    @selection_mode.setter
    def selection_mode(self, value):
        self._selecting = bool(value)
        for group in self._selections.values():
            for lfr in group:  # type: LinearFlightRegion
                lfr.setMovable(value)

    def add_patch(self, *args):
        return self.add_linked_selection(*args)
        pass

    @property
    def plots(self) -> List[AbstractSeriesPlotter]:
        return self.widget.plots

    def _check_proximity(self, x, span, proximity=0.03) -> bool:
        """
        Check the proximity of a mouse click at location 'x' in relation to
        any already existing LinearRegions.

        Parameters
        ----------
        x : float
            Mouse click position in data coordinate
        span : float
            X-axis span of the view box
        proximity : float
            Proximity as a percentage of the view box span

        Returns
        -------
        True if x is not in proximity to any existing LinearRegionItems
        False if x is within or in proximity to an existing LinearRegionItem

        """
        prox = span * proximity
        for group in self._selections.values():
            if not len(group):
                continue
            lri0 = group[0]  # type: LinearRegionItem
            lx0, lx1 = lri0.getRegion()
            if lx0 - prox <= x <= lx1 + prox:
                print("New point is too close")
                return False
        return True

    def onclick(self, ev):
        event = ev[0]
        try:
            pos = event.pos()  # type: pg.Point
        except AttributeError:
            # Avoid error when clicking around plot, due to an attempt to
            #  call mapFromScene on None in pyqtgraph/mouseEvents.py
            return
        if event.button() == QtCore.Qt.RightButton:
            return

        if event.button() == QtCore.Qt.LeftButton:
            if not self.selection_mode:
                return
            p0 = self.plots[0]
            if p0.vb is None:
                return
            event.accept()
            # Map click location to data coordinates
            xpos = p0.vb.mapToView(pos).x()
            v0, v1 = p0.get_xlim()
            vb_span = v1 - v0
            if not self._check_proximity(xpos, vb_span):
                return

            start = xpos - (vb_span * 0.05)
            stop = xpos + (vb_span * 0.05)
            self.add_linked_selection(start, stop)

    def add_linked_selection(self, start, stop, uid=None, label=None):
        """
        Add a LinearFlightRegion selection across all linked x-axes
        With width ranging from start:stop

        Labelling for the regions is not yet implemented, due to the
        difficulty of vertically positioning the text. Solution TBD
        """

        if isinstance(start, pd.Timestamp):
            start = start.value
        if isinstance(stop, pd.Timestamp):
            stop = stop.value
        patch_region = [start, stop]

        lfr_group = []
        grpid = uid or gen_uuid('flr')
        update = LineUpdate(self._flight.uid, 'add', grpid,
                            pd.to_datetime(start), pd.to_datetime(stop), None)

        for i, plot in enumerate(self.plots):
            lfr = LinearFlightRegion(parent=self)
            lfr.group = grpid
            plot.addItem(lfr)
            # plot.addItem(lfr.label)
            lfr.setRegion(patch_region)
            lfr.setMovable(self._selecting)
            lfr_group.append(lfr)
            lfr.sigRegionChanged.connect(self.update)
            # self._group_map[lfr] = grpid

        self._selections[grpid] = lfr_group
        self.line_changed.emit(update)

    def remove(self, item: LinearFlightRegion):
        if not isinstance(item, LinearFlightRegion):
            return

        grpid = item.group
        update = LineUpdate(self._flight.uid, 'remove', grpid,
                            pd.to_datetime(1), pd.to_datetime(1), None)
        grp = self._selections[grpid]
        for i, plot in enumerate(self.plots):
            plot.removeItem(grp[i].label)
            plot.removeItem(grp[i])
        del self._selections[grpid]
        self.line_changed.emit(update)

    def set_label(self, item: LinearFlightRegion, text: str):
        if not isinstance(item, LinearFlightRegion):
            return
        group = self._selections[item.group]
        for lfr in group:  # type: LinearFlightRegion
            lfr.set_label(text)

        x0, x1 = item.getRegion()
        update = LineUpdate(self._flight.uid, 'modify', item.group,
                            pd.to_datetime(x0), pd.to_datetime(x1), text)
        self.line_changed.emit(update)

    def update(self, item: LinearFlightRegion):
        """Update other LinearRegionItems in the group of 'item' to match the
        new region.
        We must set a flag here as we only want to process updates from the
        first source - as this update will be called during the update
        process because LinearRegionItem.setRegion() raises a
        sigRegionChanged event.

        A timer (_update_timer) is also used to avoid firing a line update
        with ever pixel adjustment. _update_done will be called after an elapsed
        time (100ms default) where there have been no calls to update().
        """
        if self._updating:
            return

        self._update_timer.start()
        self._updating = True
        self._line_update = item
        new_region = item.getRegion()
        group = self._selections[item.group]
        for lri in group:  # type: LinearFlightRegion
            if lri is item:
                continue
            else:
                lri.setRegion(new_region)
        self._updating = False

    def _update_done(self):
        self._update_timer.stop()
        x0, x1 = self._line_update.getRegion()
        update = LineUpdate(self._flight.uid, 'modify', self._line_update.group,
                            pd.to_datetime(x0), pd.to_datetime(x1), None)
        self.line_changed.emit(update)
        self._line_update = None
