# -*- coding: utf-8 -*-
import logging
from typing import Dict

import pandas as pd
from PyQt5.QtCore import pyqtSignal, Qt
from pyqtgraph import Point

from dgp.core import StateAction
from dgp.core.oid import OID
from .helpers import LinearSegmentGroup, LineUpdate
from .backends import GridPlotWidget, AxisFormatter

__all__ = ['TransformPlot', 'LineSelectPlot', 'AxisFormatter', 'LineUpdate']

_log = logging.getLogger(__name__)

"""
Task specific Plotting Interface definitions.

This module adds various Plotting classes based on :class:`GridPlotWidget`
which are tailored for specific tasks, e.g. the LineSelectPlot provides methods
and user-interaction features to allow a user to create line-segments (defining
a section of interesting data).

"""


class TransformPlot(GridPlotWidget):
    """Plot interface used for displaying transformation results.
    May need to display data plotted against time series or scalar series.

    Parameters
    ----------
    kwargs :
        Keyword arguments are supplied to the base :class:`GridPlotWidget`
        The TransformPlot sets sharex=True, multiy=False and timeaxis=True by
        default

        rows : int
        cols : int
        grid : bool

    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs, sharex=True, multiy=False, timeaxis=True)

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
        self._segments: Dict[OID, LinearSegmentGroup] = {}
        self.add_onclick_handler(self.onclick)

    @property
    def selection_mode(self):
        return self._selecting

    @selection_mode.setter
    def selection_mode(self, value):
        self._selecting = bool(value)
        for group in self._segments.values():
            group.set_movable(self._selecting)

    def add_segment(self, start: float, stop: float, label: str = None,
                    uid: OID = None, emit=True) -> LinearSegmentGroup:
        """
        Add a LinearSegment selection across all linked x-axes
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

        uid = uid or OID(tag='segment')
        group = LinearSegmentGroup(self.plots, uid, start, stop, label=label,
                                   movable=self._selecting)
        group.sigSegmentUpdate.connect(self.sigSegmentChanged.emit)
        group.sigSegmentUpdate.connect(self._segment_updated)
        self._segments[uid] = group

        if emit:
            update = LineUpdate(StateAction.CREATE, uid, group.left,
                                group.right, group.label_text)
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
            # call mapFromScene on None in pyqtgraph/mouseEvents.py
            return
        if event.button() == Qt.RightButton:
            return

        if event.button() == Qt.LeftButton:
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
            x0, x1 = group.region
            if x0 - prox <= x <= x1 + prox:
                _log.warning("New segment is too close to an existing segment")
                return False
        return True

    def _segment_updated(self, update: LineUpdate):
        if update.action is StateAction.DELETE:
            del self._segments[update.uid]
