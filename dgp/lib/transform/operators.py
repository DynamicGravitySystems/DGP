# coding: utf-8

from pyqtgraph.flowchart.library.common import Node, CtrlNode

import pandas as pd


class ScalarMultiply(CtrlNode):
    nodeName = 'ScalarMultiply'
    uiTemplate = [
        ('multiplier', 'spin', {'value': 1, 'step': 1, 'bounds': [None, None]}),
    ]

    def __init__(self, name):
        terminals = {
            'data_in': dict(io='in'),
            'data_out': dict(io='out'),
        }

        CtrlNode.__init__(self, name, terminals=terminals)

    def process(self, data_in, display=True):
        result = data_in * self.ctrls['multiplier'].value()
        return {'data_out': result}


# TODO: Consider how to do this for an undefined number of inputs
class ConcatenateSeries(Node):
    nodeName = 'ConcatenateSeries'

    def __init__(self, name):
        terminals = {
            'A': dict(io='in'),
            'B': dict(io='in'),
            'data_out': dict(io='out'),
        }

        Node.__init__(self, name, terminals=terminals)

    def process(self, A, B, display=True):
        result = pd.concat([A, B], join='outer', axis=1)
        return {'data_out': result}