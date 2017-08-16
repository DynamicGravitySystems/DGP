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
        figure = Figure(figsize=(width, height), dpi=dpi)
        self.axes = figure.add_subplot(111)
        self.compute_initial_figure()

        FigureCanvas.__init__(self, figure)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def compute_initial_figure(self):
        pass

    def clear(self):
        pass


class GeneralPlot(BasePlottingCanvas):
    def __init__(self, parent=None):
        BasePlottingCanvas.__init__(self, parent=parent)

    def clear(self):
        self.axes.cla()
        self.draw()

    def plot(self, df):
        # TODO: make this a more general function with ability to choose channels/method of plotting
        self.clear()
        self.axes.plot(df[df.columns[0]])
        self.draw()

    def linear_plot(self, *series):
        """
        Generate a linear plot from an arbitrary list of Pandas Series
        :param series:
        :return: None
        """
        self.clear()

        self.axes.set_title('Linear Plot')
        for data in series:
            if type(data) is Series:
                x = np.linspace(0, 1, len(data))
                self.axes.plot(x, data, label=data.name)
            else:
                continue
        self.axes.legend()
        self.draw()

    @staticmethod
    def get_toolbar(plot, parent=None):
        return NavigationToolbar(plot, parent=parent)
