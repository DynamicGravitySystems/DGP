# coding=utf-8


class Graph:
    def __init__(self):
        self._graph = {}
        self._toposort = []

    @classmethod
    def from_list(cls, inlist):
        """ Generates a graph from the given adjacency list """
        g = cls()
        g._graph = inlist
        return g

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
        """ Topological sorting of the graph """
        visited = []
        stack = []

        for node in self._graph:
            self._visit(node, visited, stack)
        return stack

