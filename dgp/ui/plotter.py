# coding: utf-8

"""
Class to handle Matplotlib plotting of data to be displayed in Qt GUI
"""

from PyQt5.QtWidgets import QSizePolicy

from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg as FigureCanvas,
                                                NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from pandas.core.series import Series
import numpy as np


class BasePlottingCanvas(FigureCanvas):
    """
    BasePlottingCanvas sets up the basic Qt Canvas parameters, and is designed
    to be subclassed for different plot types.
    """
    def __init__(self, parent=None, width=8, height=4, dpi=100):
        self.parent = parent
        figure = Figure(figsize=(width, height), dpi=dpi)

        FigureCanvas.__init__(self, figure)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        # self.axes = self.figure.add_subplot(111)
        self.axes = []

        # self.compute_initial_figure()
        self.figure.canvas.mpl_connect('button_press_event', self.onclick)
        self.figure.canvas.mpl_connect('button_release_event', self.onrelease)

    def generate_subplots(self, rows: int):
        """Generate vertically stacked subplots for comparing data"""
        # TODO: Experimenting with generating multiple plots, work with Chris on this class
        # Clear any current axes first
        self.axes = []
        i = 0
        for i in range(rows):
            if i == 0:
                sp = self.figure.add_subplot(rows, 1, i+1)
            else:  # Share x-axis with plot 0
                sp = self.figure.add_subplot(rows, 1, i+1, sharex=self.axes[0])
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


class GeneralPlot(BasePlottingCanvas):
    def __init__(self, n=1, parent=None):
        BasePlottingCanvas.__init__(self, parent=parent)
        self.resample_rule = '100ms'

    def clear(self):
        if not self.axes:
            return 0
        for axes in self.axes:
            axes.cla()
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
        for spine in focus.spines.values():
            spine.set_color('orange')

        unfocus = [ax for ax in self.axes if ax != focus]
        for ax in unfocus:
            for spine in ax.spines.values():
                spine.set_color('black')

        self.draw()

    def linear_plot(self, axes=0, *series, resample='1S'):
        """
        Generate a linear plot from an arbitrary list of Pandas Series
        :param axes: index of axes to draw the plot on
        :param series:
        :param resample:
        :return: None
        """
        if not self.axes:
            return

        self.axes[axes].cla()
        # self.axes[ind].set_title('Linear Plot')
        for data in series:
            if type(data) is Series:
                # dec_data = data[::5]
                dec_data = data.resample(resample).mean()
                x = np.linspace(0, 1, len(dec_data))
                line = self.axes[axes].plot(x, dec_data, label=data.name)
            else:
                continue
        self.axes[axes].legend()
        self.draw()

    @staticmethod
    def get_toolbar(plot, parent=None):
        return NavigationToolbar(plot, parent=parent)
