# coding: utf-8

from importlib import import_module
from pyqtgraph.flowchart.NodeLibrary import NodeLibrary, isNodeClass

__all__ = ['LIBRARY']

# from . import operators, gravity, derivatives, filters, display, timeops


_modules = []
for name in ['operators', 'gravity', 'derivatives', 'filters', 'display',
             'timeops']:
    mod = import_module('.%s' % name, __name__)
    _modules.append(mod)

LIBRARY = NodeLibrary()
for mod in _modules:
    nodes = [attr for attr in mod.__dict__.values() if isNodeClass(attr)]
    for node in nodes:
        # Control whether the Node is available to user in Context Menu
        # TODO: Add class attr to enable/disable display on per Node basis
        if hasattr(mod, '__displayed__') and not mod.__displayed__:
            path = []
        else:
            path = [(mod.__name__.split('.')[-1].capitalize(),)]
        LIBRARY.addNodeType(node, path)
