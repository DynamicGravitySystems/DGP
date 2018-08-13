# -*- coding: utf-8 -*-
import logging
from collections import namedtuple
from typing import List, Iterable, Tuple

import pandas as pd

from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtWidgets import QInputDialog, QMenu
from pyqtgraph import LinearRegionItem, TextItem, AxisItem
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent

LOG = logging.getLogger(__name__)
LineUpdate = namedtuple('LineUpdate', ['action', 'uid', 'start', 'stop',
                                       'label'])


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




class LinearSegment(LinearRegionItem):
    """Custom LinearRegionItem class to provide override methods on various
    click events.

    Parameters
    ----------
    parent : :class:`LineSelectPlot`

    """
    sigLabelChanged = pyqtSignal(object, str)
    sigDeleteRequested = pyqtSignal(object)

    def __init__(self, values=(0, 1), orientation=None, brush=None,
                 movable=True, bounds=None, parent=None, label=None):
        super().__init__(values=values, orientation=orientation, brush=brush,
                         movable=movable, bounds=bounds)

        self.parent = parent
        self._grpid = None
        self._label = TextItem(text=label or '', color=(0, 0, 0),
                               anchor=(0, 0))
        self._label_y = 0
        self._update_label_pos()
        self._menu = QMenu()
        self._menu.addAction('Remove', lambda: self.sigDeleteRequested.emit(self))
        self._menu.addAction('Set Label', self._get_label_dlg)
        self.sigRegionChanged.connect(self._update_label_pos)

    @property
    def group(self):
        return self._grpid

    @group.setter
    def group(self, value):
        self._grpid = value

    @property
    def label(self) -> str:
        return self._label.textItem.toPlainText()

    @label.setter
    def label(self, value: str) -> None:
        """Set the label text, limiting input to 10 characters"""
        self._label.setText(value[:10])
        self._update_label_pos()

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

    def y_rng_changed(self, vb, ylims):  # pragma: no cover
        """pyqtSlot (ViewBox, Tuple[Float, Float])
        Center the label vertically within the ViewBox when the ViewBox
        Y-Limits have changed

        """
        x = self._label.pos()[0]
        y = ylims[0] + (ylims[1] - ylims[0]) / 2
        self._label.setPos(x, y)

    def _update_label_pos(self):
        x0, x1 = self.getRegion()
        cx = x0 + (x1 - x0) / 2
        self._label.setPos(cx, self._label.pos()[1])

    def _get_label_dlg(self):  # pragma: no cover
        text, result = QInputDialog.getText(self.parent, "Enter Label",
                                            "Line Label:", text=self.label)
        if not result:
            return
        self.sigLabelChanged.emit(self, str(text).strip())

