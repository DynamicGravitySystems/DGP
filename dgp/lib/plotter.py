# coding: utf-8

"""
Class to handle Matplotlib plotting of data to be displayed in Qt GUI
"""

import logging
from collections import namedtuple
from typing import List

from PyQt5.QtWidgets import QSizePolicy
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg as FigureCanvas,
                                                NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter
from matplotlib.lines import Line2D

from pandas.core.series import Series
import numpy as np

from dgp.lib.types import DataCurve


class BasePlottingCanvas(FigureCanvas):
    """
    BasePlottingCanvas sets up the basic Qt Canvas parameters, and is designed
    to be subclassed for different plot types.
    """
    def __init__(self, parent=None, width=8, height=4, dpi=100):
        self.log = logging.getLogger(__name__)
        self.parent = parent
        figure = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)

        FigureCanvas.__init__(self, figure)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        # self.axes = self.figure.add_subplot(111)
        self.axes = []
        self.lines = {}

        # self.compute_initial_figure()
        self.figure.canvas.mpl_connect('button_press_event', self.onclick)
        self.figure.canvas.mpl_connect('button_release_event', self.onrelease)

    def generate_subplots(self, rows: int):
        """Generate vertically stacked subplots for comparing data"""
        # TODO: Experimenting with generating multiple plots, work with Chris on this class
        def set_x_formatter(axes):
            print("Xlimit changed")
            axes.get_xaxis().set_major_formatter(DateFormatter('%H:%M:%S'))

        # Clear any current axes first
        self.axes = []
        self.lines = {x: {} for x in range(rows)}
        i = 0
        for i in range(rows):
            if i == 0:
                sp = self.figure.add_subplot(rows, 1, i+1)
            else:  # Share x-axis with plot 0
                sp = self.figure.add_subplot(rows, 1, i+1, sharex=self.axes[0])

            sp.grid(True)
            sp.callbacks.connect('xlim_changed', set_x_formatter)
            self.axes.append(sp)
            i += 1

    def add_subplot(self):
        pass

    def compute_initial_figure(self):
        pass

    def clear(self):
        pass

    def onclick(self, event):
        pass

    def onrelease(self, event):
        pass

    def __len__(self):
        return len(self.axes)


plotline = namedtuple('plotline', ['line', 'data'])


class GeneralPlot(BasePlottingCanvas):
    def __init__(self, n=1, parent=None):
        BasePlottingCanvas.__init__(self, parent=parent)
        self._resample = '100ms'  # TODO: Add parameter for this

    def clear(self):
        for x in range(len(self.axes)):
            for line in self.lines[x].values():
                line.remove()
            self.lines[x].clear()
        self.draw()

    def onclick(self, event):
        for ax in self.axes:
            # Set the parent GUI active_plot to the axes clicked on
            if event.inaxes == ax:
                idx = self.axes.index(ax)
                self.parent.set_active_plot(idx)
                self.set_focus(idx)  # Set the color of the focused axes
            else:
                continue

    def set_focus(self, ind: int):
        """Set a colored border around the plot in focus"""
        focus = self.axes[ind]
        # focus.relim()
        # focus.autoscale_view(True, False, True)
        for spine in focus.spines.values():
            spine.set_color('orange')

        unfocus = [ax for ax in self.axes if ax != focus]
        for ax in unfocus:
            for spine in ax.spines.values():
                spine.set_color('black')

        self.draw()



    def plot_channels(self, index: int, *channels: List[DataCurve]):
        """
        Musings - working on this to replace linear_plot2

        save reference to lines and use the visible property to hide show after first plot?

        Parameters
        ----------
        index
        channels

        Returns
        -------

        """
        if not channels:
            # self.axes[index].clear()
            # for cn in self.axes[index].get_lines():
            #     self.axes[index].remove(cn)
                # cn.remove()
            # self.axes[index].get_xaxis().set_major_formatter(DateFormatter('%H:%M:%S'))
            # self.axes[index].grid(True)
            self.axes[index].relim()
            # self.axes[index].callbacks.connect('xlim_changed', lambda x: x.get_xaxis().set_major_formatter(DateFormatter('%H:%M:%S')))
            self.draw_idle()
        for cn in channels:
            print("Plotting channel")
            cn_name, data = cn
            cn_line = self.axes[index].plot(data.index.to_pydatetime(), data, label=cn_name)
            self.axes[index].get_xaxis().set_major_formatter(DateFormatter('%H:%M:%S'))
            # self.axes[index].add_line(cn_line)

        self.axes[index].relim()
        # self.axes[index].autoscale_view(True, False, True)
        # self.draw()




    def linear_resample(self, data):
        y = data.resample(self._resample).mean()
        x = np.linspace(0, 1, len(y))
        return x, y

    def linear_plot2(self, axes: int, *series: List[DataCurve]):
        """
        linear_plot2 is an improvement on the original function which stores plotted lines so that
        the data may be updated instead of completely redrawn - this is important when changing the
        plot sampling level and when the user has zoomed or panned the plot. By updating the existing
        line data we can keep the users perspective on the plot.
        :param int axes: Index of the axes to draw the series on
        :param list series: List of one or more pandas Series to plot
        :return:
        """
        if not series:
            print("No series passed to linear_plot2")
            for k, line in self.lines[axes].items():
                line.remove()
            self.lines[axes].clear()
            self.axes[axes].clear()  # This seems to fix bad scaling issue
            self.axes[axes].relim()
            self.axes[axes].autoscale_view(True, False, True)
            self.draw()
            return

        # Prune non selected lines from plot
        remove = []
        for k, line in self.lines[axes].items():
            if k not in [s.channel for s in series]:
                line.remove()
                remove.append(k)
        for item in remove:
            self.lines[axes].pop(item)

        for curve in series:
            x, y = self.linear_resample(curve.data)
            label = curve.channel
            if label not in self.lines[axes].keys():
                # Plot the data and add it to lines array
                self.lines[axes][label], = self.axes[axes].plot(x, y, label=label)
            else:
                # Update the data
                self.lines[axes][label].set_data(x, y)

        self.axes[axes].legend()
        self.axes[axes].relim()
        self.draw()
        self.axes[axes].autoscale_view(True, False, True)
        # self.log.debug("lines: {}".format(self.lines))

    @staticmethod
    def get_toolbar(plot, parent=None):
        return NavigationToolbar(plot, parent=parent)
