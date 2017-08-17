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
    def __init__(self, parent=None, width=5, height=4, dpi=100):
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

    def generate_subplots(self, rows: int, cols: int=1):
        # TODO: Experimenting with generating multiple plots, work with Chris on this class
        # Clear any current axes first
        self.axes = []
        i = 0
        for i in range(rows):
            sp = self.figure.add_subplot(rows, cols, i+1)
            self.axes.append(sp)
            i += 1

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
        self.parent.log(event)

    def plot(self, df):
        # TODO: make this a more general function with ability to choose channels/method of plotting
        self.clear()
        if self.axes:
            self.axes[0].plot(df[df.columns[0]])
            self.draw()
        else:
            self.parent.log("Axes not initialized")

    def linear_plot(self, *series):
        """
        Generate a linear plot from an arbitrary list of Pandas Series
        :param series:
        :return: None
        """
        if not self.axes:
            return

        self.clear()
        self.axes[0].set_title('Linear Plot')
        for data in series:
            if type(data) is Series:
                x = np.linspace(0, 1, len(data))
                self.axes[0].plot(x, data, label=data.name)
            else:
                continue
        self.axes[0].legend()
        self.draw()

    @staticmethod
    def get_toolbar(plot, parent=None):
        return NavigationToolbar(plot, parent=parent)
