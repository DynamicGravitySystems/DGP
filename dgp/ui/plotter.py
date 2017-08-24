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


class GeneralPlot(BasePlottingCanvas):
    def __init__(self, n=1, parent=None):
        BasePlottingCanvas.__init__(self, parent=parent)

    def clear(self):
        if not self.axes:
            return 0
        for axes in self.axes:
            axes.cla()
        self.draw()

    def onclick(self, event):
        for ax in self.axes:
            if event.inaxes == ax:
                idx = self.axes.index(ax)
                self.parent.active_plot = idx
                print("Active plot set to: {}".format(self.parent.active_plot))
                self.set_focus(self.axes.index(ax))
            else:
                continue

    def set_focus(self, ind: int):
        """Set a colored border around the plot in focus"""
        print("Setting axes border color")
        focus = self.axes[ind]
        for spine in focus.spines.values():
            spine.set_color('orange')

        unfocus = [ax for ax in self.axes if ax != focus]
        for ax in unfocus:
            for spine in ax.spines.values():
                spine.set_color('black')

        self.draw()


    def plot(self, df):
        # TODO: make this a more general function with ability to choose channels/method of plotting
        self.clear()
        if self.axes:
            self.axes[0].plot(df[df.columns[0]][::100])
            self.draw()
        else:
            self.parent.log("Axes not initialized")

    def linear_plot(self, ind=0, *series):
        """
        Generate a linear plot from an arbitrary list of Pandas Series
        :param series:
        :return: None
        """
        if not self.axes:
            return

        # self.clear()
        self.axes[ind].cla()
        # self.axes[ind].set_title('Linear Plot')
        for data in series:
            if type(data) is Series:
                dec_data = data[::5]
                x = np.linspace(0, 1, len(dec_data))

                self.axes[ind].plot(x, dec_data, label=data.name)
            else:
                continue
        self.axes[ind].legend()
        self.draw()

    @staticmethod
    def get_toolbar(plot, parent=None):
        return NavigationToolbar(plot, parent=parent)
