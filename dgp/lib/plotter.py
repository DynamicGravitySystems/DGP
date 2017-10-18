# coding: utf-8

"""
Class to handle Matplotlib plotting of data to be displayed in Qt GUI
"""

import logging
import datetime
from collections import namedtuple
from typing import List, Tuple

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QSizePolicy
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg as FigureCanvas,
                                                NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.dates import DateFormatter, num2date
from matplotlib.backend_bases import MouseEvent
from matplotlib.patches import Rectangle
from pandas import Series
import numpy as np


class BasePlottingCanvas(FigureCanvas):
    """
    BasePlottingCanvas sets up the basic Qt Canvas parameters, and is designed
    to be subclassed for different plot types.
    """
    def __init__(self, parent=None, width=8, height=4, dpi=100):
        self.log = logging.getLogger(__name__)
        self.parent = parent
        fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        FigureCanvas.__init__(self, fig)

        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self._axes = []

        self.figure.canvas.mpl_connect('button_press_event', self.onclick)
        self.figure.canvas.mpl_connect('button_release_event', self.onrelease)
        self.figure.canvas.mpl_connect('motion_notify_event', self.onmotion)

    def generate_subplots(self, rows: int) -> None:
        """Generate vertically stacked subplots for comparing data"""
        # TODO: Experimenting with generating multiple plots, work with Chris on this class
        # def set_x_formatter(axes):
        #     print("Xlimit changed")
        #     axes.get_xaxis().set_major_formatter(DateFormatter('%H:%M:%S'))

        # Clear any current axes first
        self._axes = []
        for i in range(rows):
            if i == 0:
                sp = self.figure.add_subplot(rows, 1, i+1)  # type: Axes
            else:  # Share x-axis with plot 0
                sp = self.figure.add_subplot(rows, 1, i + 1, sharex=self._axes[0])  # type: Axes

            sp.grid(True)
            # sp.xaxis_date()
            # sp.get_xaxis().set_major_formatter(DateFormatter('%H:%M:%S'))
            sp.name = 'Axes {}'.format(i)
            # sp.callbacks.connect('xlim_changed', set_x_formatter)
            self._axes.append(sp)
            i += 1

        self.compute_initial_figure()

    def add_subplot(self):
        pass

    def compute_initial_figure(self):
        pass

    def clear(self):
        pass

    def onclick(self, event: MouseEvent):
        pass

    def onrelease(self, event: MouseEvent):
        pass

    def onmotion(self, event: MouseEvent):
        pass

    def __len__(self):
        return len(self._axes)


ClickInfo = namedtuple('ClickInfo', ['partners', 'x0', 'xpos', 'ypos'])


class LineGrabPlot(BasePlottingCanvas):
    """
    LineGrabPlot implements BasePlottingCanvas and provides an onclick method to select flight
    line segments.
    """
    def __init__(self, n=1, title=None, parent=None):
        BasePlottingCanvas.__init__(self, parent=parent)
        self.rects = []
        self.zooming = False
        self.panning = False
        self.clicked = None  # type: ClickInfo
        self.generate_subplots(n)
        self.plotted = False
        self.timespan = datetime.timedelta(0)
        self.resample = slice(None, None, 20)
        self._lines = {}
        if title:
            self.figure.suptitle(title, y=1)

    def draw(self):
        self.plotted = True
        super().draw()

    def clear(self):
        self._lines = {}
        self.resample = slice(None, None, 20)
        self.draw()
        for ax in self._axes:  # type: Axes
            for line in ax.lines[:]:
                ax.lines.remove(line)
            # ax.cla()
            # ax.grid(True)
            # Reconnect the xlim_changed callback after clearing
            # ax.get_xaxis().set_major_formatter(DateFormatter('%H:%M:%S'))
            # ax.callbacks.connect('xlim_changed', self._on_xlim_changed)
        self.draw()

    def onclick(self, event: MouseEvent):
        if self.zooming or self.panning:  # Don't do anything when zooming/panning is enabled
            return

        # Check that the click event happened within one of the subplot axes
        if event.inaxes not in self._axes:
            return
        self.log.info("Xdata: {}".format(event.xdata))

        caxes = event.inaxes  # type: Axes
        other_axes = [ax for ax in self._axes if ax != caxes]
        # print("Current axes: {}\nOther axes obj: {}".format(repr(caxes), other_axes))

        for partners in self.rects:
            patch = partners[0]['rect']
            if patch.get_x() <= event.xdata <= patch.get_x() + patch.get_width():
                # Then we clicked an existing rectangle
                x0, _ = patch.xy
                self.clicked = ClickInfo(partners, x0, event.xdata, event.ydata)

                for attrs in partners:
                    rect = attrs['rect']
                    rect.set_animated(True)
                    r_canvas = rect.figure.canvas
                    r_axes = rect.axes  # type: Axes
                    r_canvas.draw()
                    attrs['bg'] = r_canvas.copy_from_bbox(r_axes.bbox)
                return

        # else: Create a new rectangle on all axes
        ylim = caxes.get_ylim()  # type: Tuple
        xlim = caxes.get_xlim()  # type: Tuple
        width = (xlim[1] - xlim[0]) * np.float64(0.01)
        # Get the bottom left corner of the rectangle which will be centered at the mouse click
        x0 = event.xdata - width/2
        y0 = ylim[0]
        height = ylim[1] - ylim[0]
        c_rect = Rectangle((x0, y0), width, height*2, alpha=0.1)

        caxes.add_patch(c_rect)
        caxes.draw_artist(caxes.patch)

        partners = [{'rect': c_rect, 'bg': None}]
        for ax in other_axes:
            x0 = event.xdata - width/2
            ylim = ax.get_ylim()
            y0 = ylim[0]
            height = ylim[1] - ylim[0]
            a_rect = Rectangle((x0, y0), width, height*2, alpha=0.1)
            ax.add_patch(a_rect)
            ax.draw_artist(ax.patch)
            partners.append({'rect': a_rect, 'bg': None})

        self.rects.append(partners)
        self.figure.canvas.draw()
        return

    def toggle_zoom(self):
        if self.panning:
            self.panning = False
        self.zooming = not self.zooming

    def toggle_pan(self):
        if self.zooming:
            self.zooming = False
        self.panning = not self.panning

    def onmotion(self, event: MouseEvent):
        if event.inaxes not in self._axes:
            return
        if self.clicked is not None:
            partners, x0, xclick, yclick = self.clicked
            dx = event.xdata - xclick
            new_x = x0 + dx
            for attrs in partners:
                rect = attrs['rect']  # type: Rectangle
                rect.set_x(new_x)
                canvas = rect.figure.canvas
                axes = rect.axes  # type: Axes
                canvas.restore_region(attrs['bg'])
                axes.draw_artist(rect)
                canvas.blit(axes.bbox)

    def onrelease(self, event: MouseEvent):
        if self.clicked is None:
            return  # Nothing Selected
        partners = self.clicked.partners
        for attrs in partners:
            rect = attrs['rect']
            rect.set_animated(False)
            rect.axes.draw_artist(rect)
            attrs['bg'] = None

        self.clicked = None
        # self.draw()

    def plot2(self, ax: Axes, series: Series):
        if self._lines.get(id(ax), None) is None:
            self._lines[id(ax)] = []
        if len(series) > 10000:
            sample_series = series[self.resample]
        else:
            # Don't resample small series
            sample_series = series
        line = ax.plot(sample_series.index, sample_series.values, label=sample_series.name)
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))

        ax.relim()
        ax.autoscale_view()
        self._lines[id(ax)].append((line, series))
        self.timespan = self._timespan(*ax.get_xlim())
        # print("Timespan: {}".format(self.timespan))
        ax.legend()

    @staticmethod
    def _timespan(x0, x1):
        return num2date(x1) - num2date(x0)

    def _on_xlim_changed(self, changed: Axes):
        """
        When the xlim changes (width of the graph), we want to apply a decimation algorithm to the
        dataset to speed up the visual performance of the graph. So when the graph is zoomed out
        we will plot only one in 20 data points, and as the graph is zoomed we will lower the decimation
        factor to zero.
        Parameters
        ----------
        changed

        Returns
        -------

        """
        # print("Xlim changed for ax: {}".format(ax))
        # TODO: Probably move this logic into its own function(s)
        delta = self._timespan(*changed.get_xlim())
        if self.timespan:
            ratio = delta/self.timespan * 100
        else:
            ratio = 100

        if 50 < ratio:
            resample = slice(None, None, 20)
        elif 10 < ratio <= 50:
            resample = slice(None, None, 10)
        else:
            resample = slice(None, None, None)
        if resample == self.resample:
            return

        self.resample = resample

        for ax in self._axes:
            if self._lines.get(id(ax), None) is not None:
                # print(self._lines[id(ax)])
                for line, series in self._lines[id(ax)]:
                    print("xshape: {}".format(series.shape))
                    r_series = series[self.resample]
                    print("Resample shape: {}".format(r_series.shape))
                    line[0].set_ydata(r_series.values)
                    line[0].set_xdata(r_series.index)
                    ax.draw_artist(line[0])
                    print("Resampling to: {}".format(self.resample))
            ax.relim()
            ax.get_xaxis().set_major_formatter(DateFormatter('%H:%M:%S'))
        self.figure.canvas.draw()

    def get_toolbar(self, parent=None) -> QtWidgets.QToolBar:
        """
        Get a Matplotlib Toolbar for the current plot instance, and set toolbar actions (pan/zoom) specific to this plot.
        Parameters
        ----------
        [parent]
            Optional Qt Parent for this object

        Returns
        -------
        QtWidgets.QToolBar : Matplotlib Qt Toolbar used to control this plot instance
        """
        toolbar = NavigationToolbar(self, parent=parent)
        toolbar.actions()[4].triggered.connect(self.toggle_pan)
        toolbar.actions()[5].triggered.connect(self.toggle_zoom)
        return toolbar

    def __getitem__(self, item):
        return self._axes[item]
