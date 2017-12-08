import os
import sys
import uuid
import logging
import datetime
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
#                                                 '../dgp')))

import PyQt5.QtWidgets as QtWidgets
import PyQt5.Qt as Qt

import numpy as np
from pandas import Series, DatetimeIndex

os.chdir('..')
import dgp.lib.project as project
import dgp.lib.plotter as plotter


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
        self.plot = plotter.LineGrabPlot(self._flight, 2)
        self.setCentralWidget(self.plot)
        # toolbar = self.plot.get_toolbar(self)
        self.show()

    def plot_sin(self):
        idx = DatetimeIndex(freq='1S', start=datetime.datetime.now(),
                            periods=1000)
        ser = Series([np.sin(x) for x in np.arange(0, 100, 0.1)], index=idx)
        dc = MockDataChannel(ser, 'SinPlot')
        dc2 = MockDataChannel(-ser, '-SinPlot')
        self.plot.add_series(dc)
        self.plot.add_series(dc2)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    _log = logging.getLogger()
    _log.addHandler(logging.StreamHandler(sys.stdout))
    _log.setLevel(logging.DEBUG)

    window = PlotExample()
    window.plot_sin()
    sys.exit(app.exec_())

