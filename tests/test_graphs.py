# coding: utf-8

import pytest
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
from dgp.lib.transform.operators import (ScalarMultiply, ConcatenateSeries,
                                         AddSeries)
from dgp.lib.transform.timeops import ComputeDelay, ShiftFrame


class TestGraphNodes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtGui.QApplication([])

        cls.library = fclib.LIBRARY.copy()
        cls.library.addNodeType(Eotvos, [('Gravity',)])
        cls.library.addNodeType(LatitudeCorrection, [('Gravity',)])
        cls.library.addNodeType(FreeAirCorrection, [('Gravity',)])
        cls.library.addNodeType(Detrend, [('Filters',)])
        cls.library.addNodeType(ScalarMultiply, [('Operators',)])
        cls.library.addNodeType(ConcatenateSeries, [('Operators',)])

        # Ensure gps_fields are ordered correctly relative to test file
        gps_fields = ['mdy', 'hms', 'lat', 'long', 'ortho_ht', 'ell_ht',
                      'num_stats', 'pdop']
        cls.data = ti.import_trajectory(
            'tests/sample_data/eotvos_short_input.txt',
            columns=gps_fields,
            skiprows=1,
            timeformat='hms'
        )

    @classmethod
    def tearDownClass(cls):
        cls.app.exit()

    def setUp(self):
        self.fc = Flowchart(terminals={
            'data_in': {'io': 'in'},
            'data_out': {'io': 'out'}
        })
        self.fc.setLibrary(self.library)

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

    @classmethod
    def setUpClass(cls):
        cls.app = QtGui.QApplication([])
        cls.library = fclib.LIBRARY.copy()
        cls.library.addNodeType(ConcatenateSeries, [('Operators',)])
        cls.library.addNodeType(AddSeries, [('Operators',)])

    def setUp(self):
        self.fc = Flowchart(terminals={
            'A': {'io': 'in'},
            'B': {'io': 'in'},
            'data_out': {'io': 'out'}
        })

        self.fc.setLibrary(self.library)

    @classmethod
    def tearDownClass(cls):
        cls.app.exit()

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

    def test_add_series(self):
        input_a = pd.Series(np.arange(0, 5), index=['A', 'B', 'C', 'D', 'E'])
        input_b = pd.Series(np.arange(2, 7), index=['A', 'B', 'C', 'D', 'E'])
        expected = input_a.astype(np.float64) + input_b.astype(np.float64)

        fnode = self.fc.createNode('AddSeries', pos=(0, 0))
        self.fc.connectTerminals(self.fc['A'], fnode['A'])
        self.fc.connectTerminals(self.fc['B'], fnode['B'])
        self.fc.connectTerminals(fnode['data_out'], self.fc['data_out'])

        result = self.fc.process(A=input_a, B=input_b)
        res = result['data_out']
        self.assertTrue(res.equals(expected))


class TestTimeOpsGraphNodes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtGui.QApplication([])
        cls.library = fclib.LIBRARY.copy()
        cls.library.addNodeType(ComputeDelay, [('Time Ops',)])
        cls.library.addNodeType(ShiftFrame, [('Time Ops',)])

    def setUp(self):
        self.fc = Flowchart(terminals={
            's1': {'io': 'in'},
            's2': {'io': 'in'},
            'data_out': {'io': 'out'}
        })

        self.fc.setLibrary(self.library)

    @classmethod
    def tearDownClass(cls):
        cls.app.exit()

    def test_compute_delay_array(self):
        rnd_offset = 1.1
        t1 = np.linspace(1, 5000, 50000, dtype=np.float64)
        t2 = t1 + rnd_offset
        s1 = np.sin(0.8 * t1) + np.sin(0.2 * t1)
        s2 = np.sin(0.8 * t2) + np.sin(0.2 * t2)

        fnode = self.fc.createNode('ComputeDelay', pos=(0, 0))
        self.fc.connectTerminals(self.fc['s1'], fnode['s1'])
        self.fc.connectTerminals(self.fc['s2'], fnode['s2'])
        self.fc.connectTerminals(fnode['data_out'], self.fc['data_out'])

        result = self.fc.process(s1=s1, s2=s2)
        res = result['data_out']

        # TODO: Kludge to make the test pass. Consider whether to admit arrays in graph processing
        self.assertAlmostEqual(rnd_offset, -res/10, places=2)

    def test_compute_delay_timelike_index(self):
        rnd_offset = 1.1
        t1 = np.arange(0, 5000, 0.1, dtype=np.float64)
        t2 = t1 + rnd_offset
        s1 = np.sin(0.8 * t1) + np.sin(0.2 * t1)
        s2 = np.sin(0.8 * t2) + np.sin(0.2 * t2)
        now = pd.Timestamp.now()
        index1 = now + pd.to_timedelta(t1, unit='s')
        frame1 = pd.Series(s1, index=index1)
        index2 = now + pd.to_timedelta(t2, unit='s')
        frame2 = pd.Series(s2, index=index2)

        fnode = self.fc.createNode('ComputeDelay', pos=(0, 0))
        self.fc.connectTerminals(self.fc['s1'], fnode['s1'])
        self.fc.connectTerminals(self.fc['s2'], fnode['s2'])
        self.fc.connectTerminals(fnode['data_out'], self.fc['data_out'])

        result = self.fc.process(s1=frame1, s2=frame2)
        res = result['data_out']

        self.assertAlmostEqual(rnd_offset, -res, places=2)

    def test_compute_delay_timelike_index_raises(self):
        rnd_offset = 1.1
        t1 = np.arange(0, 5000, 0.1, dtype=np.float64)
        t2 = t1 + rnd_offset
        s1 = np.sin(0.8 * t1) + np.sin(0.2 * t1)
        s2 = np.sin(0.8 * t2) + np.sin(0.2 * t2)
        now = pd.Timestamp.now()
        index1 = now + pd.to_timedelta(t1, unit='s')
        frame1 = pd.Series(s1, index=index1)
        frame2 = s2

        fnode = self.fc.createNode('ComputeDelay', pos=(0, 0))
        self.fc.connectTerminals(self.fc['s1'], fnode['s1'])
        self.fc.connectTerminals(self.fc['s2'], fnode['s2'])
        self.fc.connectTerminals(fnode['data_out'], self.fc['data_out'])

        msg_expected = 's2 has no index. Ignoring index for s1.'
        with self.assertWarns(UserWarning, msg=msg_expected):
            self.fc.process(s1=frame1, s2=frame2)

        frame1 = s1
        index2 = now + pd.to_timedelta(t2, unit='s')
        frame2 = pd.Series(s2, index=index2)

        msg_expected = 's1 has no index. Ignoring index for s2.'
        with self.assertWarns(UserWarning, msg=msg_expected):
            self.fc.process(s1=frame1, s2=frame2)

        frame1 = pd.Series(s1, index=index1)
        index2 = now + pd.to_timedelta(t2, unit='s')
        frame2 = pd.Series(s2)

        msg_expected = ('Index of s2 is not a DateTimeIndex. Ignoring both '
                        'indexes.')
        with self.assertWarns(UserWarning, msg=msg_expected):
            self.fc.process(s1=frame1, s2=frame2)

        frame1 = pd.Series(s1)
        index2 = now + pd.to_timedelta(t2, unit='s')
        frame2 = pd.Series(s2, index=index2)

        msg_expected = ('Index of s1 is not a DateTimeIndex. Ignoring both '
                        'indexes.')
        with self.assertWarns(UserWarning, msg=msg_expected):
            self.fc.process(s1=frame1, s2=frame2)

    def test_shift_frame(self):
        test_input = pd.Series(np.arange(10))
        index = pd.Timestamp.now() + pd.to_timedelta(np.arange(10), unit='s')
        test_input.index = index
        shifted_index = index.shift(110, freq='L')
        expected = test_input.copy()
        expected.index = shifted_index

        fnode = self.fc.createNode('ShiftFrame', pos=(0, 0))
        self.fc.connectTerminals(self.fc['s1'], fnode['frame'])
        self.fc.connectTerminals(self.fc['s2'], fnode['delay'])
        self.fc.connectTerminals(fnode['data_out'], self.fc['data_out'])

        result = self.fc.process(s1=test_input, s2=0.11)
        res = result['data_out']

        self.assertTrue(res.equals(expected))
