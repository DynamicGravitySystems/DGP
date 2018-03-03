# coding: utf-8
import pytest
from nose.tools import assert_almost_equals
import pandas as pd
import numpy as np

from dgp.lib.transform.graph import Graph, TransformGraph, GraphError
from dgp.lib.transform.gravity import eotvos_correction, latitude_correction, free_air_correction
from dgp.lib.transform.operators import concat
import dgp.lib.trajectory_ingestor as ti

from tests import sample_dir
import csv


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
        g = TransformGraph(graph=test_input)
        assert g.order == ['d', 'c', 'b', 'a']

    def test_execute(self, test_input):
        g = TransformGraph(graph=test_input)
        res = g.execute()
        expected = {'a': 1, 'b': 2, 'c': 3, 'd': 6}
        assert res == expected

    def test_graph_setter(self, test_input):
        g = TransformGraph(graph=test_input)
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

    def test_subclass_noargs(self, test_input):
        class NewTransformGraph(TransformGraph):
            transform_graph = test_input

        g = NewTransformGraph()
        res = g.execute()
        expected = {'a': 1, 'b': 2, 'c': 3, 'd': 6}
        assert res == expected

    def test_subclass_args(self):
        class NewTransformGraph(TransformGraph):
            def __init__(self, in1, in2):
                self.transform_graph = {'a': in1,
                                        'b': in2,
                                        'c': (add, 'a', 'b'),
                                        'd': (sum, ['a', 'b', 'c'])
                                        }
                super().__init__()

        g = NewTransformGraph(1, 2)
        res = g.execute()
        expected = {'a': 1, 'b': 2, 'c': 3, 'd': 6}
        assert res == expected


class TestCorrections:
    @pytest.fixture
    def trajectory_data(self):
        # Ensure gps_fields are ordered correctly relative to test file
        gps_fields = ['mdy', 'hms', 'lat', 'long', 'ortho_ht', 'ell_ht',
                      'num_stats', 'pdop']
        data = ti.import_trajectory(
            'tests/sample_data/eotvos_short_input.txt',
            columns=gps_fields,
            skiprows=1,
            timeformat='hms'
        )

        return data

    def test_eotvos(self, trajectory_data):
        # TODO: More complete test that spans the range of possible inputs
        result_eotvos = []
        with sample_dir.joinpath('eotvos_short_result.csv').open() as fd:
            test_data = csv.DictReader(fd)
            for line in test_data:
                result_eotvos.append(float(line['Eotvos_full']))

        transform_graph = {'trajectory': trajectory_data,
                           'eotvos': (eotvos_correction, 'trajectory'),
                           }
        g = TransformGraph(graph=transform_graph)
        eotvos_a = g.execute()

        for i, value in enumerate(eotvos_a['eotvos']):
            if 1 < i < len(result_eotvos) - 2:
                try:
                    assert_almost_equals(value, result_eotvos[i], places=2)
                except AssertionError:
                    print("Invalid assertion at data line: {}".format(i))
                    raise AssertionError

    def test_free_air_correction(self, trajectory_data):
        # TODO: More complete test that spans the range of possible inputs
        s1 = pd.Series([39.9148595446, 39.9148624273], name='lat')
        s2 = pd.Series([1599.197, 1599.147], name='ell_ht')
        test_input = pd.concat([s1, s2], axis=1)
        test_input.index = pd.Index([trajectory_data.index[0], trajectory_data.index[-1]])

        expected = pd.Series([-493.308594971815, -493.293177069581],
                             index=pd.Index([trajectory_data.index[0],
                                             trajectory_data.index[-1]]),
                             name='fac'
                             )

        transform_graph = {'trajectory': test_input,
                           'fac': (free_air_correction, 'trajectory'),
                           }
        g = TransformGraph(graph=transform_graph)
        res = g.execute()
        np.testing.assert_array_almost_equal(expected, res['fac'], decimal=8)

        # check that the indices are equal
        assert test_input.index.identical(res['fac'].index)

    def test_latitude_correction(self, trajectory_data):
        test_input = pd.DataFrame([39.9148595446, 39.9148624273])
        test_input.columns = ['lat']
        test_input.index = pd.Index([trajectory_data.index[0], trajectory_data.index[-1]])

        expected = pd.Series([-980162.105035777, -980162.105292394],
                             index=pd.Index([trajectory_data.index[0],
                                             trajectory_data.index[-1]]),
                             name='lat_corr'
                             )

        transform_graph = {'trajectory': test_input,
                           'lat_corr': (latitude_correction, 'trajectory'),
                           }
        g = TransformGraph(graph=transform_graph)
        res = g.execute()

        np.testing.assert_array_almost_equal(expected, res['lat_corr'], decimal=8)

        # check that the indexes are equal
        assert test_input.index.identical(res['lat_corr'].index)

