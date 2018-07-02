# -*- coding: utf-8 -*-
import pandas as pd

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QAction, QInputDialog, QMenu
from pyqtgraph import LinearRegionItem, TextItem, AxisItem


class DateAxis(AxisItem):
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
        # self.label.setPos()
        self._menu = QMenu()
        self._menu.addAction(QAction('Remove', self, triggered=self._remove))
        self._menu.addAction(QAction('Set Label', self,
                                     triggered=self._getlabel))
        self.sigRegionChanged.connect(self._move_label)

    @property
    def group(self):
        return self._grpid

    @group.setter
    def group(self, value):
        self._grpid = value

    def mouseClickEvent(self, ev):
        if not self.parent.selection_mode:
            return
        if ev.button() == Qt.RightButton and not self.moving:
            ev.accept()
            pos = ev.screenPos().toPoint()
            pop_point = QPoint(pos.x(), pos.y())
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
        text, result = QInputDialog.getText(None,
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

