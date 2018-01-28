import os
import sys
import uuid
import logging
import datetime
import traceback

from PyQt5 import QtCore
import PyQt5.QtWidgets as QtWidgets
import PyQt5.Qt as Qt
import numpy as np
from pandas import Series, DatetimeIndex
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle
from matplotlib.dates import date2num

os.chdir('..')
import dgp.lib.project as project
from dgp.gui.plotting.plotter2 import FlightLinePlot


class MockDataChannel:
    def __init__(self, series, label):
        self._series = series
        self.label = label
        self.uid = uuid.uuid4().__str__()

    def series(self):
        return self._series

    def plot(self, *args):
        pass


class PlotExample(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Plotter Testing')
        self.setBaseSize(Qt.QSize(600, 600))
        self._flight = project.Flight(None, 'test')

        self._plot = FlightLinePlot(self._flight, parent=self)
        self._plot.set_mode(grab=True)
        print("Plot: ", self._plot)
        # self.plot.figure.canvas.mpl_connect('pick_event', lambda x: print(
        #     "Pick event handled"))
        # self.plot.mgr = StackedAxesManager(self.plot.figure, rows=2)
        # self._toolbar = NavToolbar(self.plot, parent=self)
        # self._toolbar.actions()[0] = QtWidgets.QAction("Reset View")
        # self._toolbar.actions()[0].triggered.connect(lambda x: print(
        #     "Action 0 triggered"))

        self.tb = self._plot.get_toolbar()

        plot_layout = QtWidgets.QVBoxLayout()
        plot_layout.addWidget(self._plot)
        plot_layout.addWidget(self.tb)
        c_widget = QtWidgets.QWidget()
        c_widget.setLayout(plot_layout)

        self.setCentralWidget(c_widget)

        plot_layout.addWidget(QtWidgets.QPushButton("Reset"))

        # toolbar = self.plot.get_toolbar(self)
        self.show()

    def plot_sin(self):
        idx = DatetimeIndex(freq='5S', start=datetime.datetime.now(),
                            periods=1000)
        ser = Series([np.sin(x)*3 for x in np.arange(0, 100, 0.1)], index=idx)
        self.plot.mgr.add_series(ser)
        self.plot.mgr.add_series(-ser)
        ins_0 = self.plot.mgr.add_inset_axes(0)  # type: Axes
        ins_0.plot(ser.index, ser.values)
        x0, x1 = ins_0.get_xlim()
        width = (x1 - x0) * .5
        y0, y1 = ins_0.get_ylim()
        height = (y1 - y0) * .5
        # Draw rectangle patch on inset axes - proof of concept to add inset
        # locator when zoomed in on large data set.
        ax0 = self.plot.mgr[0][0]  # type: Axes
        rect = Rectangle((date2num(idx[0]), 0), width, height,
                         edgecolor='black',
                         linewidth=2, alpha=.5, fill='red')
        rect.set_picker(True)
        patch = ins_0.add_patch(rect)  # type: Rectangle
        # Future idea: Add click+drag to view patch to pan in main plot
        def update_rect(ax: Axes):
            x0, x1 = ax.get_xlim()
            y0, y1 = ax.get_ylim()
            patch.set_x(x0)
            patch.set_y(y0)
            height = y1 - y0
            width = x1 - x0
            patch.set_width(width)
            patch.set_height(height)
            ax.draw_artist(patch)
            self.plot.draw()

        ax0.callbacks.connect('xlim_changed', update_rect)
        ax0.callbacks.connect('ylim_changed', update_rect)

        self.plot.draw()
        ins_1 = self.plot.mgr.add_inset_axes(1)


def excepthook(type_, value, traceback_):
    """This allows IDE to properly display unhandled exceptions which are
    otherwise silently ignored as the application is terminated.
    Override default excepthook with
    >>> sys.excepthook = excepthook

    See: http://pyqt.sourceforge.net/Docs/PyQt5/incompatibilities.html
    """
    traceback.print_exception(type_, value, traceback_)
    QtCore.qFatal('')


if __name__ == '__main__':
    sys.excepthook = excepthook
    app = QtWidgets.QApplication(sys.argv)
    _log = logging.getLogger()
    _log.addHandler(logging.StreamHandler(sys.stdout))
    _log.setLevel(logging.DEBUG)

    window = PlotExample()
    # window.plot_sin()
    sys.exit(app.exec_())

