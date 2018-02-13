import pyqtgraph.flowchart.library as fclib

from . import derivatives, filters, gravity, operators, timeops


LIBRARY = fclib.NodeLibrary()

# Add all nodes to the default library
for mod in [derivatives, filters, gravity, operators, timeops]:
    nodes = [getattr(mod, name) for name in dir(mod)
             if fclib.isNodeClass(getattr(mod, name))]
    for node in nodes:
        LIBRARY.addNodeType(node, [(mod.NODE_TYPE,)])
