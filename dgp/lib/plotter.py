# coding: utf-8

"""
Class to handle Matplotlib plotting of data to be displayed in Qt GUI
"""

import logging
from collections import namedtuple
from typing import List, Tuple

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QSizePolicy
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg as FigureCanvas,
                                                NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.dates import DateFormatter
from matplotlib.backend_bases import MouseEvent
from matplotlib.patches import Rectangle

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
    def __init__(self, n=1, parent=None, title=None):
        BasePlottingCanvas.__init__(self, parent=parent)
        self.rects = []
        self.zooming = False
        self.panning = False
        self.clicked = None  # type: ClickInfo
        self.generate_subplots(n)
        self.plotted = False
        if title:
            self.figure.suptitle(title, y=1)

    def clear(self):
        for ax in self._axes:  # type: Axes
            ax.cla()
            ax.grid(True)
            # Reconnect the xlim_changed callback after clearing
            ax.callbacks.connect('xlim_changed', self._on_xlim_changed)
        self.draw()

    def onclick(self, event: MouseEvent):
        if self.zooming or self.panning:  # Don't do anything when zooming/panning is enabled
            return

        # Check that the click event happened within one of the subplot axes
        if event.inaxes not in self._axes:
            return

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

        partners = [{'rect': c_rect, 'bg': None}]
        for ax in other_axes:
            x0 = event.xdata - width/2
            ylim = ax.get_ylim()
            y0 = ylim[0]
            height = ylim[1] - ylim[0]
            a_rect = Rectangle((x0, y0), width, height*2, alpha=0.1)
            ax.add_patch(a_rect)
            partners.append({'rect': a_rect, 'bg': None})

        self.rects.append(partners)
        self.figure.canvas.draw()
        # self.draw()
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

    def plot(self, ax: Axes, xdata, ydata, **kwargs):
        ax.plot(xdata, ydata, **kwargs)
        ax.legend()

    @staticmethod
    def _on_xlim_changed(ax: Axes):
        ax.get_xaxis().set_major_formatter(DateFormatter('%H:%M:%S'))

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
