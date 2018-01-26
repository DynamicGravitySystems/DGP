# coding: utf-8

from pyqtgraph.flowchart.NodeLibrary import NodeLibrary, isNodeClass
from pyqtgraph.flowchart.library import Display, Data

__all__ = ['derivatives', 'filters', 'gravity', 'operators', 'LIBRARY']

from . import operators, gravity, derivatives, filters

LIBRARY = NodeLibrary()
for mod in [operators, gravity, derivatives, filters, Display, Data]:
    nodes = [getattr(mod, name) for name in dir(mod)
             if isNodeClass(getattr(mod, name))]
    for node in nodes:
        LIBRARY.addNodeType(node, [(mod.__name__.split('.')[-1],)])
