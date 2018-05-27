# coding: utf-8

from pyqtgraph.Qt import QtWidgets
from pyqtgraph.flowchart.library.common import CtrlNode

from scipy import signal
import pandas as pd
import numpy as np


class FIRLowpassFilter(CtrlNode):
    nodeName = 'FIRLowpassFilter'
    uiTemplate = [
        ('length', 'spin', {'value': 60, 'step': 1, 'bounds': [1, None]}),
        ('sample', 'spin', {'value': 0.5, 'step': 0.1, 'bounds': [0.0, None]}),
        ('channel', 'combo', {'values': []})
    ]

    def __init__(self, name):
        terminals = {
            'data_in': dict(io='in'),
            'data_out': dict(io='out'),
        }

        CtrlNode.__init__(self, name, terminals=terminals)

    def process(self, data_in, display=True):
        if display:
            self.updateList(data_in)

        channel = self.ctrls['channel'].currentText()
        if channel is not '':
            data_in = data_in[channel]

        filter_len = self.ctrls['length'].value()
        fs = self.ctrls['sample'].value()
        fc = 1 / filter_len
        nyq = fs / 2
        wn = fc / nyq
        n = int(2 * filter_len * fs)
        taps = signal.firwin(n, wn, window='blackman', nyq=nyq)
        filtered_data = signal.filtfilt(taps, 1.0, data_in, padtype='even',
                                        padlen=80)
        return {'data_out': pd.Series(filtered_data, index=data_in.index,
                                      name=channel)}

    def updateList(self, data):
        # TODO: Work on better update algo
        if isinstance(data, pd.DataFrame):
            ctrl = self.ctrls['channel']  # type: QtWidgets.QComboBox

            count = ctrl.count()
            items = [ctrl.itemText(i) for i in range(count)]
            opts = [col for col in data if col not in items]
            if opts:
                print("updating cbox with: ", opts)
                ctrl.addItems(opts)

    # def ctrlWidget(self):
    #     widget = super().ctrlWidget()
    #     widget.layout().addWidget(self.selection)
    #     return widget



# TODO: Do ndarrays with both dimensions greater than 1 work?
class Detrend(CtrlNode):
    """
    Removes a linear trend from the input dataset

    Parameters
    ----------
        data_in: :obj:`DataFrame` or list-like
            Data to detrend. If a DataFrame is given, then all channels are
            detrended.

    Returns
    -------
        :class:`DataFrame` or list-like

    """
    nodeName = 'Detrend'
    uiTemplate = [
        ('begin', 'spin', {'value': 0, 'step': 0.1, 'bounds': [None, None]}),
        ('end', 'spin', {'value': 0, 'step': 0.1, 'bounds': [None, None]})
    ]

    def __init__(self, name):
        terminals = {
            'data_in': dict(io='in'),
            'data_out': dict(io='out'),
        }

        CtrlNode.__init__(self, name, terminals=terminals)

    def process(self, data_in, display=True):
        if isinstance(data_in, pd.DataFrame):
            length = len(data_in.index)
        else:
            length = len(data_in)

        trend = np.linspace(self.ctrls['begin'].value(),
                            self.ctrls['end'].value(),
                            num=length)
        if isinstance(data_in, (pd.Series, pd.DataFrame)):
            trend = pd.Series(trend, index=data_in.index)
            result = data_in.sub(trend, axis=0)
        else:
            result = data_in - trend
        return {'data_out': result}
