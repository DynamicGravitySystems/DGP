# coding: utf-8

from pyqtgraph.flowchart.library.common import CtrlNode, Node

import numpy as np


def centraldifference(data_in, n=1, order=2, dt=0.1):
    if order == 2:
        # first derivative
        if n == 1:
            dy = (data_in[2:] - data_in[0:-2]) / (2 * dt)
        # second derivative
        elif n == 2:
            dy = ((data_in[0:-2] - 2 * data_in[1:-1] + data_in[2:]) /
                  np.power(dt, 2))
        else:
            raise ValueError('Invalid value for parameter n {1 or 2}')
    else:
        raise NotImplementedError()

    return np.pad(dy, (1, 1), 'edge')
    return dy


def gradient(data_in, dt=0.1):
    return np.gradient(data_in, dt)


class CentralDifference(CtrlNode):
    nodeName = "centraldifference"
    uiTemplate = [
        ('order', 'combo', {'values': [2, 4], 'index': 0}),
        ('n', 'combo', {'values': [1, 2], 'index': 0}),
        ('dt', 'spin', {'value': 0.1, 'step': 0.1, 'bounds': [0.0001, None]})
    ]

    def __init__(self, name):
        terminals = {
            'data_in': dict(io='in'),
            'data_out': dict(io='out'),
        }

        CtrlNode.__init__(self, name, terminals=terminals)

    def process(self, data_in, display=True):
        if self.ctrls['order'] == 2:
            # first derivative
            if self.ctrls['n'] == 1:
                dy = (data_in[2:] - data_in[0:-2]) / (2 * self.ctrls['dt'])
            # second derivative
            elif self.ctrls['n'] == 2:
                dy = ((data_in[0:-2] - 2 * data_in[1:-1] + data_in[2:]) /
                      np.power(self.ctrls['dt'], 2))
            else:
                raise ValueError('Invalid value for parameter n {1 or 2}')
        else:
            raise NotImplementedError()

        return {'data_out': np.pad(dy, (1, 1), 'edge')}