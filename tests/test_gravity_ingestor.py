# coding: utf-8

import os
import unittest
import pandas as pd
import numpy as np

from .context import dgp
from dgp.lib import gravity_ingestor as gi


class TestGravityIngestor(unittest.TestCase):
    def test_read_bitfield_default(self):
        status = pd.Series(data=[21061]*5)
        unpacked = gi._extract_bits(status)
        array = np.array([[1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0,
                           0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],]*5, dtype=np.uint8)
        expect = pd.DataFrame(data=array)
        self.assertTrue(unpacked.equals(expect))

    def test_read_bitfield_options(self):
        status = pd.Series(data=[21061]*5)
        columns = ['test1', 'test2', 'test3', 'test4']
        unpacked = gi._extract_bits(status, columns=columns, as_bool=True)
        array = np.array([[1, 0, 1, 0],]*5)
        expect = pd.DataFrame(data=array, columns=columns).astype(np.bool_)
        self.assertTrue(unpacked.equals(expect))

    def test_import_at1a_no_fill_nans(self):
        df = gi.read_at1a(os.path.abspath('tests/sample_gravity.csv'), fill_with_nans=False)
        self.assertEqual(df.shape, (9, 26))

        fields = ['gravity', 'long', 'cross', 'beam', 'temp', 'status', 'pressure', 'Etemp', 'GPSweek', 'GPSweekseconds']
        # Test and verify an arbitrary line of data against the same line in the pandas DataFrame
        line5 = [10061.171360, -0.026226, -0.094891, -0.093803, 62.253987, 21061, 39.690004, 52.263138, 1959, 219697.800]
        sample_line = dict(zip(fields, line5))

        self.assertEqual(df.gravity[4], sample_line['gravity'])
        self.assertEqual(df.long[4], sample_line['long'])
        # self.assertTrue(df.iloc[[2]].isnull().all)
        self.assertFalse(df.gps_time[8])
        # print(df[['gravity', 'long', 'cross']])

    def test_import_at1a_fill_nans(self):
        df = gi.read_at1a(os.path.abspath('tests/sample_gravity.csv'))
        self.assertEqual(df.shape, (9, 26))

        fields = ['gravity', 'long', 'cross', 'beam', 'temp', 'status', 'pressure', 'Etemp', 'GPSweek', 'GPSweekseconds']
        # Test and verify an arbitrary line of data against the same line in the pandas DataFrame
        line5 = [10061.171360, -0.026226, -0.094891, -0.093803, 62.253987, 21061, 39.690004, 52.263138, 1959, 219697.800]
        sample_line = dict(zip(fields, line5))

        self.assertEqual(df.gravity[5], sample_line['gravity'])
        self.assertEqual(df.long[5], sample_line['long'])
        self.assertTrue(df.iloc[[2]].isnull().all)
        # print(df[['gravity', 'long', 'cross']])
