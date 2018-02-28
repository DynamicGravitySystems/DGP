# coding=utf-8
from copy import copy
from functools import partial


class TransformGraph:
    # TODO: Use magic methods for math ops where available

    def __init__(self, graph):
        self._transform_graph = graph
        self._graph = self._make_graph()
        self._order = self._graph._toposort()
        self._results = None
        self._graph_changed = False

    @property
    def graph(self):
        return self._transform_graph

    @graph.setter
    def graph(self, g):
        self._transform_graph = g
        self._graph = self._make_graph()
        self._order = self._graph._toposort()
        self._graph_changed = True

    @property
    def results(self):
        return self._results

    def _make_graph(self):
        adjacency_list = {k: [] for k in self._transform_graph}

        for k in self._transform_graph:
            node = self._transform_graph[k]
            if isinstance(node, tuple):
                args = list(node[1:])
                for i in args:
                    adjacency_list[k] += list(i)
        return Graph(adjacency_list)

    def execute(self):
        if not self._graph_changed:
            return self._results
        else:
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
                print(new_tup)
                return partial(*new_tup)

            while order:
                k = order.pop()
                node = self._transform_graph[k]
                if isinstance(node, tuple):
                    f = _tuple_to_func(node)
                    results[k] = f()
                else:
                    results[k] = self._transform_graph[k]
            self._results = results
            self._graph_changed = False
            return self._results

    def __str__(self):
        return str(self._transform_graph)


class Graph:
    def __init__(self, graph):
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
            raise Exception('Graph cycle detected.')

        visited.append(node)
        for i in self._graph[node]:
            self._visit(i, visited, stack)

        stack.insert(0, node)

    def _toposort(self):
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

