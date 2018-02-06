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
from dgp.gui.plotting.plotters import PqtLineSelectPlot as LineSelectPlot
from pyqtgraph.graphicsItems.LinearRegionItem import LinearRegionItem


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

        self._plot = LineSelectPlot(flight=self._flight, rows=3)
        self._plot.line_changed.connect(lambda upd: print(upd))
        # self.plot.figure.canvas.mpl_connect('pick_event', lambda x: print(
        #     "Pick event handled"))
        # self.plot.mgr = StackedAxesManager(self.plot.figure, rows=2)
        # self._toolbar = NavToolbar(self.plot, parent=self)
        # self._toolbar.actions()[0] = QtWidgets.QAction("Reset View")
        # self._toolbar.actions()[0].triggered.connect(lambda x: print(
        #     "Action 0 triggered"))

        self.setCentralWidget(self._plot.widget)

        self.show()

        idx = DatetimeIndex(freq='5S', start=datetime.datetime.now(),
                            periods=1000)
        ser = Series([np.sin(x)*3 for x in np.arange(0, 100, 0.1)], index=idx)
        p0 = self._plot.plots[0]
        p0.add_series(ser)
        print("new xlim: ", p0.get_xlim())
        x0, x1 = p0.get_xlim()
        xrng = x1 - x0
        tenpct = xrng * .1

        # lri = LinearRegionItem()
        # lri.sigRegionChanged.connect(lambda rng: print("LRI Range changed to: ",
        #                                             rng.getRegion()))
        # p0.addItem(lri)
        # lri.setRegion([x0, x0+tenpct])


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

