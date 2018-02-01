# coding: utf-8

from pyqtgraph.flowchart.library.common import Node
import pandas as pd

from ..timesync import find_time_delay, shift_frame


class ComputeDelay(Node):
    nodeName = 'ComputeDelay'

    def __init__(self, name):
        terminals = {
            's1': dict(io='in'),
            's2': dict(io='in'),
            'data_out': dict(io='out'),
        }

        Node.__init__(self, name, terminals=terminals)

    def process(self, s1, s2, display=True):
        delay = find_time_delay(s1, s2)
        return {'data_out': delay}


class ShiftFrame(Node):
    nodeName = 'ShiftFrame'

    def __init__(self, name):
        terminals = {
            'frame': dict(io='in'),
            'delay': dict(io='in'),
            'data_out': dict(io='out'),
        }

        Node.__init__(self, name, terminals=terminals)

    def process(self, frame, delay, display=True):
        shifted = shift_frame(frame, delay)
        return {'data_out': shifted}
