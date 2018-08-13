# -*- coding: utf-8 -*-
import logging
import weakref
from collections import namedtuple
from typing import List, Iterable, Tuple

import pandas as pd

from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QObject
from PyQt5.QtWidgets import QInputDialog, QMenu
from pyqtgraph import LinearRegionItem, TextItem, AxisItem, PlotItem
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent

from dgp.core import OID, StateAction

_log = logging.getLogger(__name__)

LineUpdate = namedtuple('LineUpdate',
                        ['action', 'uid', 'start', 'stop', 'label'])


class PolyAxis(AxisItem):
    """AxisItem which can display tick strings formatted for a date/time value,
    or as scalar values.

    Parameters
    ----------
    orientation : str, optional
    timeaxis : bool, optional
        Enable the time-axis formatter, default is False
    kwargs
        See :class:`~pyqtgraph.graphicsItems.AxisItem.AxisItem` for allowed
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
        # Select the first formatter where the scale (sec/min/hour/day etc) is
        # greater than the range
        fmt = next((fmt for period, fmt in sorted(self._timescales.items())
                    if period >= spacing), '%m-%d')

        labels = []
        for i, loc in enumerate(values):
            try:
                ts: pd.Timestamp = pd.Timestamp(loc)
            except (OverflowError, ValueError, OSError):
                _log.exception(f'Exception converting {loc} to date string.')
                labels.append('')
                continue

            try:
                if i == 0 and len(values) > 2:
                    label = ts.strftime('%d-%b-%y %H:%M:%S')
                else:
                    label = ts.strftime(fmt)
            except ValueError:
                _log.warning("Timestamp conversion out-of-bounds")
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


class LinearSegment(LinearRegionItem):
    """Custom LinearRegionItem class used to interactively select data segments.

    Parameters
    ----------
    plot : :class:`PlotItem`
    values : tuple of float, float
        Initial left/right values for the segment
    uid : :class:`~dgp.core.OID`
    label : str, optional

    """
    sigLabelChanged = pyqtSignal(str)
    sigDeleteRequested = pyqtSignal(object)

    def __init__(self, plot: PlotItem, values, label=None,
                 brush=None, movable=False, bounds=None):
        super().__init__(values=values, orientation=LinearRegionItem.Vertical,
                         brush=brush, movable=movable, bounds=bounds)
        self._plot = weakref.ref(plot)
        self._label = TextItem(text=label or '', color=(0, 0, 0), anchor=(0, 0))
        self._update_label_pos()
        self._menu = QMenu()
        self._menu.addAction('Remove', lambda: self.sigDeleteRequested.emit(self))
        self._menu.addAction('Set Label', self._get_label_dlg)
        self.sigRegionChanged.connect(self._update_label_pos)

        plot.addItem(self)
        plot.addItem(self._label)
        plot.sigYRangeChanged.connect(self.y_rng_changed)

    @property
    def label_text(self) -> str:
        return self._label.textItem.toPlainText()

    @label_text.setter
    def label_text(self, value: str):
        """Set the label text, limiting input to 10 characters"""
        self._label.setText(value[:10])
        self._update_label_pos()

    def remove(self) -> None:
        """Remove this segment from the plot"""
        self._plot().removeItem(self._label)
        self._plot().removeItem(self)
        try:
            self._plot().sigYRangeChanged.disconnect(self.y_rng_changed)
        except TypeError:
            pass

    def mouseClickEvent(self, ev: MouseClickEvent):
        """Intercept right-click on segment to display context menu

        This click handler will check if the segments are editable (movable),
        if so, right-clicks will activate a context menu, left-clicks will be
        passed to the super-class to handle resizing/moving.
        """
        if not self.movable:
            return
        elif ev.button() == Qt.RightButton and not self.moving:
            ev.accept()
            pos = ev.screenPos().toPoint()
            self._menu.popup(pos)
        else:
            return super().mouseClickEvent(ev)

    def y_rng_changed(self, vb, ylims):  # pragma: no cover
        """Update label position on change of ViewBox y-limits"""
        x = self._label.pos()[0]
        y = ylims[1]
        self._label.setPos(x, y)

    def _update_label_pos(self):
        """Update label position to new segment/view bounds"""
        x0, _ = self.getRegion()
        _, y1 = self._plot().viewRange()[1]
        self._label.setPos(x0, y1)

    def _get_label_dlg(self):  # pragma: no cover
        # TODO: Assign parent or create dialog with Icon
        text, result = QInputDialog.getText(None, "Enter Label", "Segment Label:",
                                            text=self.label_text)
        if result:
            self.sigLabelChanged.emit(str(text).strip())


class LinearSegmentGroup(QObject):
    """Container for related LinearSegments which are linked across multiple
    plots

    LinearSegmentGroup encapsulates the logic required to create and update a
    set of LinearSegment's across a group of plot items.

    Parameters
    ----------
    plots : Iterable of :class:`PlotItem`
        Iterable object containing plots to add LinearSegments to. Must have at
        least 1 item.
    group : :class:`~dgp.core.OID`
        Unique identifier for this LinearSegmentGroup
    left, right : float
        Initial left/right (x) values for the segments in this group.
    label : str, optional
        Optional label to display on each segment
    movable : bool, optional
        Set the initial movable state of the segments, default is False

    Attributes
    ----------
    sigSegmentUpdate : pyqtSignal(LineUpdate)
        Qt Signal, emits a :class:`LineUpdate` object when the segment group has
        been mutated (Updated/Deleted)

    Notes
    -----
    An update timer (QTimer) is utilized to rate-limit segment update signal
    emissions during resize operations. Instead of a signal being emitted for
    every discrete movement/drag-resize of a segment, updates are emitted only
    when the timer expires. The timer is also reset with every movement so that
    updates are not triggered until the user has momentarily paused dragging, or
    finished their movement.
    
    """
    sigSegmentUpdate = pyqtSignal(object)

    def __init__(self, plots: Iterable[PlotItem], uid: OID,
                 left: float, right: float, label: str = '',
                 movable: bool = False, parent: QObject = None):
        super().__init__(parent=parent)
        self._uid = uid
        self._segments: List[LinearSegment] = []
        self._label_text = label
        self._updating = False
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._update_done)

        for plot in plots:
            segment = LinearSegment(plot, (left, right), label=label,
                                    movable=movable)
            segment.sigRegionChanged.connect(self._update_region)
            segment.sigLabelChanged.connect(self._update_label)
            segment.sigDeleteRequested.connect(self.delete)
            self._segments.append(segment)

    @property
    def left(self) -> pd.Timestamp:
        return pd.to_datetime(self._segments[0].getRegion()[0])

    @property
    def right(self) -> pd.Timestamp:
        return pd.to_datetime(self._segments[0].getRegion()[1])

    @property
    def region(self) -> Tuple[float, float]:
        for segment in self._segments:
            return segment.getRegion()

    @property
    def movable(self) -> bool:
        return self._segments[0].movable

    @property
    def label_text(self) -> str:
        return self._label_text

    def set_movable(self, movable: bool):
        for segment in self._segments:
            segment.setMovable(movable)

    def _update_label(self, label: str):
        for segment in self._segments:
            segment.label_text = label
        self._label_text = label
        self._emit_update(StateAction.UPDATE)

    def _update_region(self, segment: LinearSegment):
        """Update sibling segments to new region bounds"""
        if self._updating:
            return
        else:
            self._updating = True
            self._timer.start()
        for seg in [x for x in self._segments if x is not segment]:
            seg.setRegion(segment.getRegion())
        self._updating = False

    def _update_done(self):
        """Emit an update object when the rate-limit timer has expired"""
        self._timer.stop()
        self._emit_update(StateAction.UPDATE)

    def delete(self):
        """Delete all child segments and emit a DELETE update"""
        for segment in self._segments:
            segment.remove()
        self._emit_update(StateAction.DELETE)

    def _emit_update(self, action: StateAction = StateAction.UPDATE):
        """Emit a LineUpdate object with the current segment parameters

        Creates and emits a LineUpdate named-tuple with the current left and
        right x-values of the segment, and the current label-text.

        Parameters
        ----------
        action : StateAction, optional
            Optionally specify the action for the update, defaults to UPDATE.
            Use this parameter to trigger a DELETE action for instance.

        """
        update = LineUpdate(action, self._uid, self.left, self.right,
                            self._label_text)
        self.sigSegmentUpdate.emit(update)
