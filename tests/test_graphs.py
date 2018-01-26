# coding: utf-8

from .context import dgp, APP

import unittest
import csv
from pyqtgraph.flowchart import Flowchart
import pyqtgraph.flowchart.library as fclib
from pyqtgraph.Qt import QtGui
import pandas as pd
import numpy as np

from tests import sample_dir
import dgp.lib.trajectory_ingestor as ti
from dgp.lib.transform.gravity import (Eotvos, LatitudeCorrection,
                                       FreeAirCorrection)
from dgp.lib.transform.filters import Detrend
from dgp.lib.transform.operators import ScalarMultiply, ConcatenateSeries


class TestGraphNodes(unittest.TestCase):
    def setUp(self):
        # self.app = QtGui.QApplication([])
        self.fc = Flowchart(terminals={
            'data_in': {'io': 'in'},
            'data_out': {'io': 'out'}
        })

        library = fclib.LIBRARY.copy()
        library.addNodeType(Eotvos, [('Gravity',)])
        library.addNodeType(LatitudeCorrection, [('Gravity',)])
        library.addNodeType(FreeAirCorrection, [('Gravity',)])
        library.addNodeType(Detrend, [('Filters',)])
        library.addNodeType(ScalarMultiply, [('Operators',)])
        library.addNodeType(ConcatenateSeries, [('Operators',)])
        self.fc.setLibrary(library)

        # Ensure gps_fields are ordered correctly relative to test file
        gps_fields = ['mdy', 'hms', 'lat', 'long', 'ortho_ht', 'ell_ht',
                      'num_stats', 'pdop']
        self.data = ti.import_trajectory(
            'tests/sample_data/eotvos_short_input.txt',
            columns=gps_fields,
            skiprows=1,
            timeformat='hms'
        )

    def test_eotvos_node(self):
        # TODO: More complete test that spans the range of possible inputs
        result_eotvos = []
        with sample_dir.joinpath('eotvos_short_result.csv').open() as fd:
            test_data = csv.DictReader(fd)
            for line in test_data:
                result_eotvos.append(float(line['Eotvos_full']))

        fnode = self.fc.createNode('Eotvos', pos=(0, 0))
        self.fc.connectTerminals(self.fc['data_in'], fnode['data_in'])
        self.fc.connectTerminals(fnode['data_out'], self.fc['data_out'])

        result = self.fc.process(data_in=self.data)
        eotvos_a = result['data_out']

        for i, value in enumerate(eotvos_a):
            if 1 < i < len(result_eotvos) - 2:
                try:
                    self.assertAlmostEqual(value, result_eotvos[i], places=2)
                except AssertionError:
                    print("Invalid assertion at data line: {}".format(i))
                    raise AssertionError

    def test_free_air_correction(self):
        # TODO: More complete test that spans the range of possible inputs
        s1 = pd.Series([39.9148595446, 39.9148624273], name='lat')
        s2 = pd.Series([1599.197, 1599.147], name='ell_ht')
        test_input = pd.concat([s1, s2], axis=1)
        test_input.index = pd.Index([self.data.index[0], self.data.index[-1]])

        expected = pd.Series([-493.308594971815, -493.293177069581],
                             index=pd.Index([self.data.index[0],
                                            self.data.index[-1]]),
                             name='fac'
                             )

        fnode = self.fc.createNode('FreeAirCorrection', pos=(0, 0))
        self.fc.connectTerminals(self.fc['data_in'], fnode['data_in'])
        self.fc.connectTerminals(fnode['data_out'], self.fc['data_out'])

        result = self.fc.process(data_in=test_input)
        res = result['data_out']

        np.testing.assert_array_almost_equal(expected, res, decimal=8)

        # check that the indices are equal
        self.assertTrue(test_input.index.identical(res.index))

    def test_latitude_correction(self):
        test_input = pd.DataFrame([39.9148595446, 39.9148624273])
        test_input.columns = ['lat']
        test_input.index = pd.Index([self.data.index[0], self.data.index[-1]])

        expected = pd.Series([-980162.105035777, -980162.105292394],
                             index=pd.Index([self.data.index[0],
                                             self.data.index[-1]]),
                             name='lat_corr'
                             )

        fnode = self.fc.createNode('LatitudeCorrection', pos=(0, 0))
        self.fc.connectTerminals(self.fc['data_in'], fnode['data_in'])
        self.fc.connectTerminals(fnode['data_out'], self.fc['data_out'])

        result = self.fc.process(data_in=test_input)
        res = result['data_out']

        np.testing.assert_array_almost_equal(expected, res, decimal=8)

        # check that the indexes are equal
        self.assertTrue(test_input.index.identical(res.index))

    def test_detrend_series(self):
        test_input = pd.Series(np.arange(5), index=['A', 'B', 'C', 'D', 'E'])
        expected = pd.Series(np.zeros(5), index=['A', 'B', 'C', 'D', 'E'])

        fnode = self.fc.createNode('Detrend', pos=(0, 0))
        self.fc.connectTerminals(self.fc['data_in'], fnode['data_in'])
        self.fc.connectTerminals(fnode['data_out'], self.fc['data_out'])
        fnode.ctrls['begin'].setValue(test_input[0])
        fnode.ctrls['end'].setValue(test_input[-1])

        result = self.fc.process(data_in=test_input)
        res = result['data_out']
        self.assertTrue(res.equals(expected))

        # check that the indexes are equal
        self.assertTrue(test_input.index.identical(res.index))

    def test_detrend_ndarray(self):
        test_input = np.linspace(2, 20, num=10)
        expected = np.linspace(0, 0, num=10)

        fnode = self.fc.createNode('Detrend', pos=(0, 0))
        self.fc.connectTerminals(self.fc['data_in'], fnode['data_in'])
        self.fc.connectTerminals(fnode['data_out'], self.fc['data_out'])
        fnode.ctrls['begin'].setValue(test_input[0])
        fnode.ctrls['end'].setValue(test_input[-1])

        result = self.fc.process(data_in=test_input)
        res = result['data_out']
        np.testing.assert_array_equal(expected, res)

    def test_detrend_dataframe(self):
        s1 = pd.Series(np.arange(0, 5))
        s2 = pd.Series(np.arange(2, 7))
        test_input = pd.concat([s1, s2], axis=1)
        test_input.index = ['A', 'B', 'C', 'D', 'E']

        s1 = pd.Series(np.zeros(5))
        s2 = pd.Series(np.ones(5) * 2)
        expected = pd.concat([s1, s2], axis=1)
        expected.index = ['A', 'B', 'C', 'D', 'E']

        fnode = self.fc.createNode('Detrend', pos=(0, 0))
        self.fc.connectTerminals(self.fc['data_in'], fnode['data_in'])
        self.fc.connectTerminals(fnode['data_out'], self.fc['data_out'])
        fnode.ctrls['begin'].setValue(0)
        fnode.ctrls['end'].setValue(4)

        result = self.fc.process(data_in=test_input)
        res = result['data_out']

        self.assertTrue(res.equals(expected))

        # check that the indexes are equal
        self.assertTrue(test_input.index.identical(res.index))

    def test_scalar_multiply(self):
        test_input = pd.DataFrame(np.ones((5, 5)),
                                  index=['A', 'B', 'C', 'D', 'E'])
        expected = pd.DataFrame(np.ones((5, 5)) * 3,
                                index=['A', 'B', 'C', 'D', 'E'])

        fnode = self.fc.createNode('ScalarMultiply', pos=(0, 0))
        self.fc.connectTerminals(self.fc['data_in'], fnode['data_in'])
        self.fc.connectTerminals(fnode['data_out'], self.fc['data_out'])
        fnode.ctrls['multiplier'].setValue(3)

        result = self.fc.process(data_in=test_input)
        res = result['data_out']

        self.assertTrue(res.equals(expected))


class TestBinaryOpsGraphNodes(unittest.TestCase):
    def setUp(self):
        # self.app = QtGui.QApplication([])
        # self.app = QtWidgets.QApplication([])
        self.fc = Flowchart(terminals={
            'A': {'io': 'in'},
            'B': {'io': 'in'},
            'data_out': {'io': 'out'}
        })

        library = fclib.LIBRARY.copy()
        library.addNodeType(ConcatenateSeries, [('Operators',)])
        self.fc.setLibrary(library)

    def test_concat_series(self):
        input_A = pd.Series(np.arange(0, 5), index=['A', 'B', 'C', 'D', 'E'])
        input_B = pd.Series(np.arange(2, 7), index=['A', 'B', 'C', 'D', 'E'])
        expected = pd.concat([input_A, input_B], axis=1)

        fnode = self.fc.createNode('ConcatenateSeries', pos=(0, 0))
        self.fc.connectTerminals(self.fc['A'], fnode['A'])
        self.fc.connectTerminals(self.fc['B'], fnode['B'])
        self.fc.connectTerminals(fnode['data_out'], self.fc['data_out'])

        result = self.fc.process(A=input_A, B=input_B)
        res = result['data_out']

        self.assertTrue(res.equals(expected))

        # check that the indexes are equal
        self.assertTrue(input_A.index.identical(res.index))
        self.assertTrue(input_B.index.identical(res.index))