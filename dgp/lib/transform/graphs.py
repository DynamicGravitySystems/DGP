# coding: utf-8
from collections import OrderedDict
from copy import deepcopy

from pyqtgraph.flowchart import Flowchart, Node
from dgp.lib import transform
from dgp.lib.etc import gen_uuid


class TransformWrapper:
    """
    Container for graphs and the resulting DataFrames
    """

    def __init__(self, gravity, trajectory, flowchart):
        """
        TransformWrapper _init__ method

        Parameters
        ----------
        gravity : :obj:`DataFrame`
            Sensor data
        trajectory : :obj:`DataFrame`
            Trajectory data
        flowchart : :obj:`FlowChart`
            Process graph

        """
        self._gravity = gravity
        self._trajectory = trajectory

        self._results = {}
        self._graphs = {}
        self._origin_graph = flowchart
        self._most_recent = None

    @property
    def graph(self):
        """ :obj:`FlowChart`: Original process graph """
        return self._graph

    @property
    def most_recent(self):
        """ :obj:`DataFrame`: Most recent result """
        if self._most_recent is not None:
            return self._results[self._most_recent]

    @property
    def gravity(self):
        """ :obj:`DataFrame`: Gravity data """
        return self._gravity

    @property
    def trajectory(self):
        """ :obj:`DataFrame`: Trajectory data """
        return self._trajectory

    @property
    def results(self):
        """ dict: All results """
        return self._results

    def get_result(self, uid):
        """
        Result of process graph with uid

        Returns
        -------
        :obj:`DataFrame`:
        """
        if uid in self._results:
            return self._results[uid]

    def get_graph(self, uid):
        """
        Process graph with uid

        Returns
        -------
        :obj:`FlowChart`:
        """
        if uid in self._graphs:
            return self._graphs[uid]

    def pop_result(self, id, include_graph=False):
        """
        Removes and returns result

        Parameters
        ----------
        id: str
            UID of result to remove
        include_graph: boolean, optional
            Pops both result and graph and returns a tuple

        Returns
        -------
        :obj:`DataFrame`, tuple(:obj:`DataFrame`, :obj:`FlowChart`)
        """
        if include_graph:
            return self._graphs.pop(id, None), self._results.pop(id, None)
        else:
            return self._results.pop(id, None)

    def process_graph(self, id=None, **kwargs):
        """
        Process graph

        Processes data through the graph

        Parameters
        ----------
        id: str, optional
            UID for previously graph. If not specified, then a new graph is
            added and processed.

        """
        if id is None:
            uid = gen_uuid('tf')
            self._graphs = deepcopy(self._graphs)
        elif id in self._graphs:
            uid = id

        self._results[uid] = self._graphs[uid].process(**kwargs)
        return uid

    def __len__(self):
        return len(self._results.items())


def add_n_series(n, term_prefix='in_', output_term='result'):
    # TODO: Does not currently accommodate multipliers in the sum
    """
    Generates a flowchart to add an arbitrary number of series

    AddSeries nodes are chained to produce a flowchart that can be used
    as a node in other flowcharts

    Parameters
    ----------
        n: int
            number of series to add
        term_prefix: str, optional
            prefix for terminal labels
        output_term: str, optional
            name for the output terminal

    Returns
    -------
        :obj:`Flowchart`
    """
    if n < 2:
        raise ValueError('Cannot add fewer than 2 Series')

    terminals = {term_prefix + str(i): {'io': 'in'} for i in range(n)}
    inputs = list(terminals.keys())
    terminals[output_term] = {'io': 'out'}
    terminals['result_name'] = {'io': 'in'}

    fc = Flowchart(terminals=terminals, library=transform.LIBRARY)
    current_node = fc.createNode('AddSeries')
    fc.connectTerminals(fc[inputs[0]], current_node['A'])
    fc.connectTerminals(fc[inputs[1]], current_node['B'])
    fc.connectTerminals(fc['result_name'], current_node['result_name'])

    for k in inputs[2:]:
        next_node = fc.createNode('AddSeries')
        fc.connectTerminals(current_node['data_out'], next_node['A'])
        current_node = next_node
        fc.connectTerminals(fc[k], current_node['B'])
        fc.connectTerminals(fc['result_name'], current_node['result_name'])

    fc.connectTerminals(current_node['data_out'], fc[output_term])
    return fc


def concat_n_series(n, term_prefix='in_', output_term='result'):
    if n < 2:
        raise ValueError('Cannot concatenate fewer than 2 Series')

    d = {term_prefix + str(i): {'io': 'in'} for i in range(n)}
    terminals = OrderedDict(sorted(d.items(), key=lambda x: x[0]))
    inputs = list(terminals.keys())
    terminals[output_term] = {'io': 'out'}

    fc = Flowchart(terminals=terminals, library=transform.LIBRARY)
    current_node = fc.createNode('ConcatenateSeries')
    fc.connectTerminals(fc[inputs[0]], current_node['A'])
    fc.connectTerminals(fc[inputs[1]], current_node['B'])

    for k in inputs[2:]:
        next_node = fc.createNode('ConcatenateSeries')
        fc.connectTerminals(current_node['data_out'], next_node['A'])
        current_node = next_node
        fc.connectTerminals(fc[k], current_node['B'])

    fc.connectTerminals(current_node['data_out'], fc[output_term])
    return fc


def _string_node(value):
    class StringNode(Node):
        nodeName = 'StringNode'

        def __init__(self, name):
            self.value = None
            terminals = {
                'string': dict(io='out'),
            }

            Node.__init__(self, name, terminals=terminals)

        def process(self, display=True):
            return {'string': self.value}

    node = StringNode('StringNode')
    node.value = value
    return node


def base_graph():
    fc = Flowchart(terminals={
        'trajectory': {'io': 'in'},
        'result': {'io': 'out'}
    }, library=transform.LIBRARY)

    # compute corrections
    eotvos = fc.createNode('Eotvos')
    lat_corr = fc.createNode('LatitudeCorrection')
    fac = fc.createNode('FreeAirCorrection')

    fc.connectTerminals(fc['trajectory'], eotvos['data_in'])
    fc.connectTerminals(fc['trajectory'], lat_corr['data_in'])
    fc.connectTerminals(fc['trajectory'], fac['data_in'])

    # sum corrections
    sum_corrections = add_n_series(3)
    fc.addNode(sum_corrections, 'sum_corrections')

    sum_result_name = _string_node('corrections')
    fc.addNode(sum_result_name, 'sum_result_name')

    fc.connectTerminals(eotvos['data_out'], sum_corrections['in_0'])
    fc.connectTerminals(lat_corr['data_out'], sum_corrections['in_1'])
    fc.connectTerminals(fac['data_out'], sum_corrections['in_2'])
    fc.connectTerminals(sum_result_name['string'], sum_corrections['result_name'])

    # concatenate individual corrections and sum into single DataFrame
    cat_corrections = concat_n_series(4)
    fc.addNode(cat_corrections, 'cat_corrections')

    fc.connectTerminals(eotvos['data_out'], cat_corrections['in_0'])
    fc.connectTerminals(lat_corr['data_out'], cat_corrections['in_1'])
    fc.connectTerminals(fac['data_out'], cat_corrections['in_2'])
    fc.connectTerminals(sum_corrections['result'], cat_corrections['in_3'])

    fc.connectTerminals(cat_corrections['result'], fc['result'])

    return fc

