# coding: utf-8

from typing import Dict

from matplotlib.axes import Axes
from pyqtgraph.flowchart import Node, Terminal

"""Containing display Nodes to translate between pyqtgraph Flowchart and an
MPL plot"""


class MPLPlotNode(Node):
    nodeName = 'MPLPlotNode'

    def __init__(self, name, axes=None):
        terminals = {'In': dict(io='in', multi=True)}
        super().__init__(name=name, terminals=terminals)
        self.plot = axes

    def disconnected(self, localTerm, remoteTerm):
        """Called when connection is removed"""
        if localTerm is self['In']:
            pass

    def process(self, In: Dict, display=True) -> None:
        if display and self.plot is not None:
            for name, val in In.items():
                print("Plotter has:")
                print("Name: ", name, "\nValue: ", val)
                if val is None:
                    continue



