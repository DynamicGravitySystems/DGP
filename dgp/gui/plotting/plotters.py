# -*- coding: utf-8 -*-
import logging

import pandas as pd
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import pyqtSignal
from pyqtgraph import PlotItem, Point

from dgp.core import AxisFormatter
from dgp.core import StateAction
from dgp.core.oid import OID
from dgp.core.types.tuples import LineUpdate
from .helpers import LinearFlightRegion
from .backends import GridPlotWidget

from pyqtgraph.graphicsItems.LinearRegionItem import LinearRegionItem

"""
Task specific Plotting Interface definitions.

This module adds various Plotting classes based on :class:`GridPlotWidget`
which are tailored for specific tasks, e.g. the LineSelectPlot provides methods
and user-interaction features to allow a user to create line-segments (defining
a section of interesting data).

"""
_log = logging.getLogger(__name__)


class TransformPlot(GridPlotWidget):
    """Plot interface used for displaying transformation results.
    May need to display data plotted against time series or scalar series.
    """

    # TODO: Duplication of params? Use kwargs?
    def __init__(self, rows=1, cols=1, grid=True, parent=None):
        super().__init__(rows=rows, cols=cols, grid=grid, sharex=True,
                         multiy=False, timeaxis=True, parent=parent)

    def set_axis_formatters(self, formatter: AxisFormatter):
        for i in range(self.rows):
            self.set_xaxis_formatter(formatter, i, 0)


class LineSelectPlot(GridPlotWidget):
    """LineSelectPlot

    """
    sigSegmentChanged = pyqtSignal(LineUpdate)

    def __init__(self, rows=1, parent=None):
        super().__init__(rows=rows, cols=1, grid=True, sharex=True,
                         multiy=True, timeaxis=True, parent=parent)

        self._selecting = False
        self._segments = {}
        self._updating = False

        # Rate-limit line updates using a timer.
        self._line_update: LinearFlightRegion = None
        self._update_timer = QtCore.QTimer(self)
        self._update_timer.setInterval(100)
        self._update_timer.timeout.connect(self._update_done)

        self.add_onclick_handler(self.onclick)

    @property
    def selection_mode(self):
        return self._selecting

    @selection_mode.setter
    def selection_mode(self, value):
        self._selecting = bool(value)
        for group in self._segments.values():
            for lfr in group:  # type: LinearFlightRegion
                lfr.setMovable(value)

    def add_segment(self, start: float, stop: float, label: str = None,
                    uid: OID = None, emit=True) -> None:
        """
        Add a LinearFlightRegion selection across all linked x-axes
        With width ranging from start:stop and an optional label.

        To non-interactively add a segment group (e.g. when loading a saved
        project) this method should be called with the uid parameter, and emit
        set to False.

        Parameters
        ----------
        start : float
        stop : float
        label : str, Optional
            Optional text label to display within the segment on the plot
        uid : :class:`OID`, Optional
            Specify the uid of the segment group, used for re-creating segments
            when loading a plot
        emit : bool, Optional
            If False, sigSegmentChanged will not be emitted on addition of the
            segment

        """

        if isinstance(start, pd.Timestamp):
            start = start.value
        if isinstance(stop, pd.Timestamp):
            stop = stop.value
        patch_region = [start, stop]

        grpid = uid or OID(tag='segment')
        # Note pd.to_datetime(scalar) returns pd.Timestamp
        update = LineUpdate(StateAction.CREATE, grpid,
                            pd.to_datetime(start), pd.to_datetime(stop), label)

        lfr_group = []
        for i, plot in enumerate(self.plots):
            lfr = LinearFlightRegion(parent=self, label=label)
            lfr.group = grpid
            plot.addItem(lfr)
            plot.addItem(lfr._label)
            lfr.setRegion(patch_region)
            lfr.setMovable(self._selecting)
            lfr.sigRegionChanged.connect(self._update_segments)
            lfr.sigLabelChanged.connect(self.set_label)
            lfr.sigDeleteRequested.connect(self.remove_segment)
            plot.sigYRangeChanged.connect(lfr.y_changed)

            lfr_group.append(lfr)

        self._segments[grpid] = lfr_group
        if emit:
            self.sigSegmentChanged.emit(update)

    def get_segment(self, uid: OID):
        return self._segments[uid][0]

    def remove_segment(self, item: LinearFlightRegion):
        """Remove the segment 'item' and all of its siblings (in the same group)

        """
        if not isinstance(item, LinearFlightRegion):
            raise TypeError(f'{item!r} is not a valid type. Expected '
                            f'LinearFlightRegion')

        grpid = item.group
        x0, x1 = item.getRegion()
        update = LineUpdate(StateAction.DELETE, grpid,
                            pd.to_datetime(x0), pd.to_datetime(x1), None)
        grp = self._segments[grpid]
        for i, plot in enumerate(self.plots):
            lfr: LinearFlightRegion = grp[i]
            try:
                plot.sigYRangeChanged.disconnect(lfr.y_changed)
            except TypeError:  # pragma: no cover
                pass
            plot.removeItem(lfr._label)
            plot.removeItem(lfr)
        del self._segments[grpid]
        self.sigSegmentChanged.emit(update)

    def set_label(self, item: LinearFlightRegion, text: str):
        """Set the text label of every LFR in the same group as item"""
        if not isinstance(item, LinearFlightRegion):
            raise TypeError(f'Item must be of type LinearFlightRegion')
        group = self._segments[item.group]
        for lfr in group:  # type: LinearFlightRegion
            lfr.label = text

        x0, x1 = item.getRegion()
        update = LineUpdate(StateAction.UPDATE, item.group,
                            pd.to_datetime(x0), pd.to_datetime(x1), text)
        self.sigSegmentChanged.emit(update)

    def onclick(self, ev):  # pragma: no cover
        """Onclick handler for mouse left/right click.

        Create a new data-segment if _selection_mode is True on left-click
        """
        event = ev[0]
        try:
            pos: Point = event.pos()
        except AttributeError:
            # Avoid error when clicking around plot, due to an attempt to
            #  call mapFromScene on None in pyqtgraph/mouseEvents.py
            return
        if event.button() == QtCore.Qt.RightButton:
            return

        if event.button() == QtCore.Qt.LeftButton:
            if not self.selection_mode:
                return
            p0 = self.get_plot(row=0)
            if p0.vb is None:
                return
            event.accept()
            # Map click location to data coordinates
            xpos = p0.vb.mapToView(pos).x()
            v0, v1 = self.get_xlim(0)
            vb_span = v1 - v0
            if not self._check_proximity(xpos, vb_span):
                return

            start = xpos - (vb_span * 0.05)
            stop = xpos + (vb_span * 0.05)
            self.add_segment(start, stop)

    def _update_segments(self, item: LinearFlightRegion):
        """Update other LinearRegionItems in the group of 'item' to match the
        new region.
        A flag (_updating) is set here as we only want to process updates from
        the first item - as this function will be called during the update
        process by each item in the group when LinearRegionItem.setRegion()
        emits a sigRegionChanged event.

        A timer (_update_timer) is also used to avoid emitting a
        :class:`LineUpdate` with every pixel adjustment.
        _update_done will be called after the QTimer times-out (100ms default)
        in order to emit the intermediate or final update.

        """
        if self._updating:
            return

        self._update_timer.start()
        self._updating = True
        self._line_update = item
        new_region = item.getRegion()
        group = self._segments[item.group]
        for lri in [i for i in group if i is not item]:
            lri.setRegion(new_region)
        self._updating = False

    def _update_done(self):
        """Called when the update_timer times out to emit the completed update

        Create a :class:`LineUpdate` with the modified line segment parameters
        start, stop, _label

        """
        self._update_timer.stop()
        x0, x1 = self._line_update.getRegion()
        update = LineUpdate(StateAction.UPDATE, self._line_update.group,
                            pd.to_datetime(x0), pd.to_datetime(x1), None)
        self.sigSegmentChanged.emit(update)
        self._line_update = None

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
        for group in self._segments.values():
            lri0 = group[0]  # type: LinearRegionItem
            lx0, lx1 = lri0.getRegion()
            if lx0 - prox <= x <= lx1 + prox:
                print("New point is too close")
                return False
        return True
