# coding: utf-8
from copy import copy
from functools import partial
from collections.abc import Iterable


class GraphError(Exception):
    def __init__(self, graph, message):
        self.graph = graph
        self.message = message


class TransformGraph:
    def __init__(self, graph=None):
        if graph is not None:
            self.transform_graph = graph
        self._init_graph()
        self._results = None
        self._graph_changed = True

    @classmethod
    def run(cls, *args, item=None):
        """
        Use the graph as a node in another graph

        Parameters
        ----------
        *args
            arguments to pass to graph initializer

        item: str or list of str
            keys of the results graph to be returned

        Returns
        -------
            Function whose output is the result of the graph according to the
            keys specified
        """
        def func(*args):
            c = cls(*args)
            results = c.execute()
            if item is None:
                return results
            else:
                return results[item]
        return func

    def _init_graph(self):
        """
        Initialize the transform graph

        This is an internal method.
        Do not modify the transform graph in place. Instead, use the setter.
        """
        self._graph = self._make_graph()
        self._order = self._graph.topo_sort()

    @property
    def order(self):
        return self._order

    @property
    def graph(self):
        """ iterable: Transform graph

        Setter recomputes a topological sorting of the new graph.
        """
        return self.transform_graph

    @graph.setter
    def graph(self, g):
        self.transform_graph = g
        self._init_graph()
        self._graph_changed = True

    @property
    def results(self):
        """ dict: Most recent result"""
        return self._results

    def _make_graph(self):
        adjacency_list = {k: [] for k in self.transform_graph}

        for k in self.transform_graph:
            node = self.transform_graph[k]
            if isinstance(node, tuple):
                for x in node[1:]:
                    if isinstance(x, str):
                        adjacency_list[k].append(x)
                    else:
                        adjacency_list[k] += x
        return Graph(adjacency_list)

    def execute(self):
        """ Execute the transform graph """
        if self._graph_changed:
            order = copy(self._order)
            results = {}

            def _tuple_to_func(tup):
                func = tup[0]
                args = []
                for arg in tup[1:]:
                    # TODO: Account for any kind of iterable, including generators.
                    if isinstance(arg, list):
                        args.append([results[x] for x in arg])
                    else:
                        args.append(results[arg])
                new_tup = tuple([func] + args)
                return partial(*new_tup)

            while order:
                k = order.pop()
                node = self.transform_graph[k]
                if isinstance(node, tuple):
                    f = _tuple_to_func(node)
                    results[k] = f()
                else:
                    results[k] = self.transform_graph[k]
            self._results = results
            self._graph_changed = False

        return self._results

    def __str__(self):
        return str(self.transform_graph)


class Graph:
    def __init__(self, graph):
        if not isinstance(graph, Iterable):
            raise TypeError('Cannot construct graph from type {typ}'
                            .format(typ=type(graph)))

        if all(isinstance(x, Iterable) and not isinstance(x, (str, bytes, bytearray)) for x in graph):
            raise TypeError('Graph must contain all iterables')

        self._graph = graph
        self._topo = []

    def add_edge(self, u, v):
        """ Add an edge to the graph """
        self._graph[u].append(v)
        if v not in self._graph:
            self._graph[v] = []

    def remove_edge(self, u, v):
        """ Remove an edge from the graph """
        self._graph[u].remove(v)

    def _visit(self, node, visited, stack):
        if node in stack:
            return
        elif node in visited:
            raise GraphError(self._graph, 'Cycle detected')

        visited.append(node)
        for i in self._graph[node]:
            self._visit(i, visited, stack)

        stack.insert(0, node)

    def topo_sort(self):
        """
        Topological sorting of the graph

        Returns
        -------
            list
                Order of execution as a stack
        """
        visited = []
        stack = []

        for node in self._graph:
            self._visit(node, visited, stack)
        return stack

    def __str__(self):
        return str(self._graph)

