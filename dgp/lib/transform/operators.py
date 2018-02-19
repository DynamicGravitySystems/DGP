# coding: utf-8

from pyqtgraph.flowchart.library.common import Node, CtrlNode

import pandas as pd

NODE_TYPE = 'Operators'


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
        # dedup column names
        if isinstance(A, pd.DataFrame) and isinstance(B, pd.Series):
            if B.name is not None and B.name in A.columns:
                B = B.rename(B.name + '_B', axis=1)
        elif isinstance(B, pd.DataFrame) and isinstance(A, pd.Series):
            if A.name is not None and A.name in B.columns:
                A = A.rename(A.name + '_A', axis=1)
        elif isinstance(A, pd.Series) and isinstance(B, pd.Series):
            if A.name is not None and B.name is not None and A.name == B.name:
                B = B.rename(B.name + '_B', axis=1)
        elif isinstance(A, pd.DataFrame) and isinstance(B, pd.DataFrame):
            rename_cols = {}
            for b in B.columns:
                if b is not None and b in A.columns:
                    rename_cols[b] = b + '_B'
            if rename_cols:
                B = B.rename(columns=rename_cols)

        result = pd.concat([A, B], join='outer', axis=1)
        return {'data_out': result}


class AddSeries(CtrlNode):
    nodeName = 'AddSeries'
    uiTemplate = [
        ('A multiplier', 'spin', {'value': 1, 'step': 1, 'bounds': [None, None]}),
        ('B multiplier', 'spin', {'value': 1, 'step': 1, 'bounds': [None, None]}),
    ]

    def __init__(self, name):
        terminals = {
            'A': dict(io='in'),
            'B': dict(io='in'),
            'result_name': dict(io='in'),
            'data_out': dict(io='out'),
        }

        CtrlNode.__init__(self, name, terminals=terminals)

    def process(self, A, B, result_name, display=True):
        if not isinstance(A, pd.Series):
            raise TypeError('Input A is not a Series, got {typ}'
                            .format(typ=type(A)))
        if not isinstance(B, pd.Series):
            raise TypeError('Input B is not a Series, got {typ}'
                            .format(typ=type(B)))

        if A.shape != B.shape:
            raise ValueError('Shape of A is {ashape} and shape of '
                             'B is {bshape}'.format(ashape=A.shape,
                                                    bshape=B.shape))
        a = self.ctrls['A multiplier'].value()
        b = self.ctrls['B multiplier'].value()

        result = a * A + b * B
        result.name = result_name
        return {'data_out': result}