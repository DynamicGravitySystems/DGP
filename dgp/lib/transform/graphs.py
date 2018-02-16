# coding: utf-8
from collections import OrderedDict

from pyqtgraph.flowchart import Flowchart
from dgp.lib import transform


class TransformWrapper:
    """
    A container for transformed DataFrames. Multiple transform graphs may
    be specified and the resultant DataFrames will be held in this class
    instance.
    """
    def __init__(self, gravity, trajectory):
        self._gdf = gravity
        self._tdf = trajectory

        self.modified = {}
        self._transform_graphs = {}
        self._defaultgraph = None

    def removegraph(self, uid):
        del self._transform_graphs[uid]
        del self.modified[uid]

    def processgraph(self, tg, **kwargs):
        if not isinstance(tg, Flowchart):
            raise TypeError('expected an instance or subclass of '
                            'Flowchart, but got {typ}'
                            .format(typ=type(tg)))

        if tg.uid not in self._transform_graphs:
            self._transform_graphs[tg.uid] = tg
            if self._defaultgraph is None:
                self._defaultgraph = self._transform_graphs[tg.uid]

        self.modified[tg.uid] = self._transform_graphs[tg.uid].process(**kwargs)
        return self.modified[tg.uid]

    @property
    def data(self, reapply=False):
        if self._defaultgraph is not None:
            if reapply:
                return self.processgraph(self._defaultgraph)
            else:
                return self.modified[self._defaultgraph.uid]
        else:
            return {'gravity': self._gdf, 'trajectory': self._tdf}

    @property
    def gravity(self):
        return self._gdf

    @property
    def trajectory(self):
        return self._tdf

    def __len__(self):
        return len(self.modified.items())


def add_n_series(series_list, term_prefix='in_', output_term='result'):
    # TODO: This function may be unnecessary if terminals can take multiple inputs
    # TODO: Related: investigate allowedAddOutput arg for Node to add inputs for n-ary ops
    """
    Generates a flowchart to add an arbitrary number of series

    AddSeries nodes are chained to produce a flowchart that can be used
    as a node in other flowcharts

    Parameters
    ----------
        series_list: list-like
            Series to add together

        term_prefix: str, optional
            prefix for terminal labels

        output_term: str, optional
            name for the output terminal

    Returns
    -------
        :obj:`Flowchart`
    """
    if len(series_list) < 2:
        raise ValueError('Cannot add fewer than 2 Series')

    d = {term_prefix + str(i): {'io': 'in'} for i in range(len(series_list))}
    terminals = OrderedDict(sorted(d.items(), key=lambda x: x[0]))
    inputs = list(terminals.keys())
    terminals[output_term] = {'io': 'out'}

    fc = Flowchart(terminals=terminals, library=transform.LIBRARY)
    current_node = fc.createNode('AddSeries')
    fc.connectTerminals(fc[inputs[0]], current_node['A'])
    fc.connectTerminals(fc[inputs[1]], current_node['B'])

    for k in inputs[2:]:
        next_node = fc.createNode('AddSeries')
        fc.connectTerminals(current_node['data_out'], next_node['A'])
        current_node = next_node
        fc.connectTerminals(fc[k], current_node['B'])

    fc.connectTerminals(current_node['data_out'], fc[output_term])
    return fc
