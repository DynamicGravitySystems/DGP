from pyqtgraph.flowchart import Flowchart
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import pyqtgraph.flowchart.library as fclib
from pyqtgraph.flowchart.library.common import CtrlNode

from scipy import signal
import numpy as np
import sys
import pandas as pd


class LowpassFilter(CtrlNode):
    nodeName = "LowpassFilter"
    uiTemplate = [
        ('cutoff', 'spin', {'value': 0.5, 'step': 0.1, 'bounds': [0.0, None]}),
        ('sample', 'spin', {'value': 0.5, 'step': 0.1, 'bounds': [0.0, None]})
    ]

    def __init__(self, name):
        terminals = {
            'dataIn': dict(io='in'),
            'dataOut': dict(io='out'),
        }

        CtrlNode.__init__(self, name, terminals=terminals)

    def process(self, dataIn, display=True):
        fc = self.ctrls['cutoff'].value()
        fs = self.ctrls['sample'].value()
        filter_len = 1 / fc
        nyq = fs / 2.0
        wn = fc / nyq
        n = int(2.0 * filter_len * fs)
        taps = signal.firwin(n, wn, window='blackman', nyq=nyq)
        filtered_data = signal.filtfilt(taps, 1.0, dataIn, padtype='even', padlen=80)
        result = pd.Series(filtered_data, index=dataIn.index)
        return {'dataOut': result}


app = QtGui.QApplication([])
win = QtGui.QMainWindow()
cw = QtGui.QWidget()
win.setCentralWidget(cw)
layout = QtGui.QGridLayout()
cw.setLayout(layout)

fc = Flowchart(terminals={
    'dataIn': {'io': 'in'},
    'dataOut': {'io': 'out'}
})

layout.addWidget(fc.widget(), 0, 0, 2, 1)
pw1 = pg.PlotWidget()
pw2 = pg.PlotWidget()
layout.addWidget(pw1, 0, 1)
layout.addWidget(pw2, 1, 1)

win.show()

fs = 100 # Hz
frequencies = [1.2, 3, 5, 7] # Hz
start = 0
stop = 10 # s
rng = pd.date_range('1/9/2017', periods=fs * (stop - start), freq='L')
t = np.linspace(start, stop, fs * (stop - start))
sig = np.zeros(len(t))
for f in frequencies:
    sig += np.sin(2 * np.pi * f * t)
ts = pd.Series(sig, index=rng)

fc.setInput(dataIn=ts)

plotList = {'Top Plot': pw1, 'Bottom Plot': pw2}

pw1Node = fc.createNode('PlotWidget', pos=(0, -150))
pw1Node.setPlotList(plotList)
pw1Node.setPlot(pw1)

pw2Node = fc.createNode('PlotWidget', pos=(150, -150))
pw2Node.setPlotList(plotList)
pw2Node.setPlot(pw2)

fclib.registerNodeType(LowpassFilter, [('Filters',)])

fnode = fc.createNode('LowpassFilter', pos=(0,0))
fnode.ctrls['cutoff'].setValue(5)
fnode.ctrls['sample'].setValue(100)

fc.connectTerminals(fc['dataIn'], fnode['dataIn'])
fc.connectTerminals(fc['dataIn'], pw1Node['In'])
fc.connectTerminals(fnode['dataOut'], pw2Node['In'])
fc.connectTerminals(fnode['dataOut'], fc['dataOut'])

if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
    QtGui.QApplication.instance().exec_()