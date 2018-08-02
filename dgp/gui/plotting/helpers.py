# -*- coding: utf-8 -*-
import logging
from datetime import datetime

import numpy as np
import pandas as pd

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QInputDialog, QMenu
from pyqtgraph import LinearRegionItem, TextItem, AxisItem
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent

LOG = logging.getLogger(__name__)


class PolyAxis(AxisItem):
    """Subclass of PyQtGraph :class:`AxisItem` which can display tick strings
    for a date/time value, or scalar values.

    Parameters
    ----------
    orientation : str
    timeaxis : bool
    kwargs

    """
    def __init__(self, orientation='bottom', timeaxis=False, **kwargs):
        super().__init__(orientation, **kwargs)
        self.timeaxis = timeaxis

        # Define time-format scales for time-range <= key
        self._timescales = {
            pd.Timedelta(seconds=1).value: '%M:%S:%f',
            pd.Timedelta(minutes=1).value: '%M:%S',
            pd.Timedelta(hours=1).value: '%H:%M:%S',
            pd.Timedelta(days=1).value: '%d %H:%M',
            pd.Timedelta(weeks=1).value: '%m-%d %H'
        }

    def dateTickStrings(self, values, spacing):
        """Create formatted date strings for the tick locations specified by
        values.

        Parameters
        ----------
        values : List
        spacing : float

        Returns
        -------
        List[str]
            List of string labels corresponding to each input value.

        """
        # Get the first formatter where the scale (sec/min/hour/day etc) is
        # greater than the range
        fmt = next((fmt for period, fmt in sorted(self._timescales.items())
                    if period >= spacing), '%m-%d')

        labels = []
        for i, loc in enumerate(values):
            try:
                ts: pd.Timestamp = pd.Timestamp(loc)
            except (OverflowError, ValueError, OSError):
                LOG.exception(f'Exception converting {loc} to date string.')
                labels.append('')
                continue

            try:
                if i == 0 and len(values) > 2:
                    label = ts.strftime('%d-%b-%y %H:%M:%S')
                else:
                    label = ts.strftime(fmt)
            except ValueError:
                LOG.warning("Timestamp conversion out-of-bounds")
                label = 'OoB'

            labels.append(label)
        return labels

    def tickStrings(self, values, scale, spacing):
        """Return the tick strings that should be placed next to ticks.

        This method overrides the base implementation in :class:`AxisItem`, and
        will selectively provide date formatted strings if :attr:`timeaxis` is
        True. Otherwise the base method is called to provide the tick strings.


        Parameters
        ----------
        values : List
            List of values to return strings for
        scale : Scalar
            Used to specify the scale of the values, useful when the axis label
            is configured to show the display as some SI fraction (e.g. milli),
            the scaled display value can be properly calculated.
        spacing : Scalar
            Spacing between values/ticks

        Returns
        -------
        List[str]
            List of strings used to label the plot at the given values

        Notes
        -----
        This function may be called multiple times for the same plot,
        where multiple tick-levels are defined i.e. Major/Minor/Sub-Minor ticks.
        The range of the values may also differ between invocations depending on
        the positioning of the chart. And the spacing will be different
        dependent on how the ticks were placed by the tickSpacing() method.

        """
        if self.timeaxis:
            return self.dateTickStrings(values, spacing)
        else:  # pragma: no cover
            return super().tickStrings(values, scale, spacing)

    def tickValues(self, minVal, maxVal, size):
        return super().tickValues(minVal, maxVal, size)

    def tickSpacing(self, minVal, maxVal, size):
        return super().tickSpacing(minVal, maxVal, size)


# TODO: Deprecated
class DateAxis(AxisItem):  # pragma: no cover
    minute = pd.Timedelta(minutes=1).value
    hour = pd.Timedelta(hours=1).value
    day = pd.Timedelta(days=2).value

    def tickStrings(self, values, scale, spacing):
        """

        Parameters
        ----------
        values : List
            List of values to return strings for
        scale : Scalar
            Used for SI notation prefixes
        spacing : Scalar
            Spacing between values/ticks

        Returns
        -------
        List of strings used to label the plot at the given values

        Notes
        -----
        This function may be called multiple times for the same plot,
        where multiple tick-levels are defined i.e. Major/Minor/Sub-Minor ticks.
        The range of the values may also differ between invocations depending on
        the positioning of the chart. And the spacing will be different
        dependent on how the ticks were placed by the tickSpacing() method.

        """
        if not values:
            rng = 0
        else:
            rng = max(values) - min(values)

        labels = []
        # TODO: Maybe add special tick format for first tick
        if rng < self.minute:
            fmt = '%H:%M:%S'

        elif rng < self.hour:
            fmt = '%H:%M:%S'
        elif rng < self.day:
            fmt = '%H:%M'
        else:
            if spacing > self.day:
                fmt = '%y:%m%d'
            elif spacing >= self.hour:
                fmt = '%H'
            else:
                fmt = ''

        for x in values:
            try:
                labels.append(pd.to_datetime(x).strftime(fmt))
            except ValueError:  # Windows can't handle dates before 1970
                labels.append('')
            except OSError:
                pass
        return labels

    def tickSpacing(self, minVal, maxVal, size):
        """
        The return value must be a list of tuples, one for each set of ticks::

            [
                (major tick spacing, offset),
                (minor tick spacing, offset),
                (sub-minor tick spacing, offset),
                ...
            ]

        """
        rng = pd.Timedelta(maxVal - minVal).value
        # offset = pd.Timedelta(seconds=36).value
        offset = 0
        if rng < pd.Timedelta(minutes=5).value:
            mjrspace = pd.Timedelta(seconds=15).value
            mnrspace = pd.Timedelta(seconds=5).value
        elif rng < self.hour:
            mjrspace = pd.Timedelta(minutes=5).value
            mnrspace = pd.Timedelta(minutes=1).value
        elif rng < self.day:
            mjrspace = pd.Timedelta(hours=1).value
            mnrspace = pd.Timedelta(minutes=5).value
        else:
            return [(pd.Timedelta(hours=12).value, offset)]

        spacing = [
            (mjrspace, offset),  # Major
            (mnrspace, offset)   # Minor
        ]
        return spacing


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
        self._label_y = 0
        self._move_label(self)
        self._menu = QMenu()
        self._menu.addAction('Remove', self._remove)
        self._menu.addAction('Set Label', self._getlabel)
        self.sigRegionChanged.connect(self._move_label)

    @property
    def group(self):
        return self._grpid

    @group.setter
    def group(self, value):
        self._grpid = value

    def mouseClickEvent(self, ev: MouseClickEvent):
        if not self.parent.selection_mode:
            return
        elif ev.button() == Qt.RightButton and not self.moving:
            ev.accept()
            pos = ev.screenPos().toPoint()
            pop_point = QPoint(pos.x(), pos.y())
            self._menu.popup(pop_point)
        else:
            return super().mouseClickEvent(ev)

    def _move_label(self, lfr):
        x0, x1 = self.getRegion()
        cx = x0 + (x1 - x0) / 2
        self.label.setPos(cx, self.label.pos()[1])

    def _remove(self):
        try:
            self.parent.remove_segment(self)
        except AttributeError:
            return

    def _getlabel(self):
        text, result = QInputDialog.getText(None, "Enter Label", "Line Label:",
                                            text=self._label_text)
        if not result:
            return
        try:
            self.parent.set_label(self, str(text).strip())
        except AttributeError:
            return

    def y_changed(self, vb, ylims):
        """pyqtSlot (ViewBox, Tuple[Float, Float])
        Center the label vertically within the ViewBox when the ViewBox
        Y-Limits have changed

        """
        x = self.label.pos()[0]
        y = ylims[0] + (ylims[1] - ylims[0]) / 2
        self.label.setPos(x, y)

    def set_label(self, text):
        self._label_text = text[:10]
        self.label.setText(self._label_text)
        self._move_label(self)

    # TODO: Add dialog action to manually adjust left/right bounds
