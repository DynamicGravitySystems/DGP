# coding: utf-8
import pytest

from dgp.lib.transform.graph import Graph, TransformGraph, GraphError


class TestGraph:
    @pytest.mark.parametrize('test_input', ['some_string',
                                            [[1, 2], [3], "hello"],
                                            {'a': [1, 2], 'b': 3},
                                            {'a': [1, 2], 'b': "hello"},
                                            ])
    def test_init_raises(self, test_input):
        pytest.raises(TypeError, Graph(test_input))

    def test_topo_sort_raises(self):
        test_input = {'a': [],
                      'b': ['c'],
                      'c': ['a', 'b'],
                      'd': ['a', 'b', 'c']}

        g = Graph(test_input)
        with pytest.raises(GraphError, message='Cycle detected'):
            g.topo_sort()


def add(a, b):
    return a + b


class TestTransformGraph:
    @pytest.fixture
    def test_input(self):
        graph = {'a': 1,
                 'b': 2,
                 'c': (add, 'a', 'b'),
                 'd': (sum, ['a', 'b', 'c'])
                 }
        return graph

    def test_init(self, test_input):
        g = TransformGraph(test_input)
        assert g.order == ['d', 'c', 'b', 'a']

    def test_execute(self, test_input):
        g = TransformGraph(test_input)
        res = g.execute()
        expected = {'a': 1, 'b': 2, 'c': 3, 'd': 6}
        assert res == expected

    def test_graph_setter(self, test_input):
        g = TransformGraph(test_input)
        g.execute()
        new_graph = {'a': 1,
                     'b': 2,
                     'c': (add, 'a', 'b'),
                     'd': (sum, ['a', 'b', 'c']),
                     'e': (add, 'd', 'b')
                    }
        g.graph = new_graph
        res = g.execute()
        expected = {'a': 1, 'b': 2, 'c': 3, 'd': 6, 'e': 8}

        assert res == expected
