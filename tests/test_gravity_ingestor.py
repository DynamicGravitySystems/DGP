# coding: utf-8

import os
import unittest
import pandas as pd
import numpy as np
import datetime

from .context import dgp
from dgp.lib import gravity_ingestor as gi


class TestGravityIngestor(unittest.TestCase):
    def test_read_bitfield_default(self):
        status = pd.Series(data=[21061]*5)
        unpacked = gi._extract_bits(status)
        array = np.array([[1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0,
                           0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],]*5,
                         dtype=np.uint8)

        expect = pd.DataFrame(data=array)
        self.assertTrue(unpacked.equals(expect))

    def test_read_bitfield_options(self):
        status = pd.Series(data=[21061]*5)

        # test num columns specified less than num bits
        columns = ['test1', 'test2', 'test3', 'test4']
        unpacked = gi._extract_bits(status, columns=columns, as_bool=True)
        array = np.array([[1, 0, 1, 0],] * 5)
        expect = pd.DataFrame(data=array, columns=columns).astype(np.bool_)
        self.assertTrue(unpacked.equals(expect))

        # test num columns specified greater than num bits
        columns = ['test' + str(i) for i in range(1,35)]
        unpacked = gi._extract_bits(status, columns=columns, as_bool=True)
        array = np.array([[1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0,
                           0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],]*5,
                         dtype=np.uint8)

        expect_cols = ['test' + str(i) for i in range(1, 33)]
        expect = pd.DataFrame(data=array, columns=expect_cols).astype(np.bool_)
        self.assertTrue(unpacked.equals(expect))
        np.testing.assert_array_equal(unpacked.columns, expect.columns)

        # test num columns specified equal to num bits
        columns = ['test' + str(i) for i in range(1,33)]
        unpacked = gi._extract_bits(status, columns=columns, as_bool=True)
        array = np.array([[1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0,
                           0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],]*5,
                         dtype=np.uint8)

        expect_cols = ['test' + str(i) for i in range(1, 33)]
        expect = pd.DataFrame(data=array, columns=expect_cols).astype(np.bool_)
        self.assertTrue(unpacked.equals(expect))
        np.testing.assert_array_equal(unpacked.columns, expect.columns)

    def test_import_at1a_no_fill_nans(self):
        df = gi.read_at1a(os.path.abspath('tests/sample_gravity.csv'), fill_with_nans=False)
        self.assertEqual(df.shape, (9, 26))

        fields = ['gravity', 'long_accel', 'cross_accel', 'beam', 'temp', 'status', 'pressure', 'Etemp', 'GPSweek', 'GPSweekseconds']
        # Test and verify an arbitrary line of data against the same line in the pandas DataFrame
        line5 = [10061.171360, -0.026226, -0.094891, -0.093803, 62.253987, 21061, 39.690004, 52.263138, 1959, 219697.800]
        sample_line = dict(zip(fields, line5))

        self.assertEqual(df.gravity[4], sample_line['gravity'])
        self.assertEqual(df.long_accel[4], sample_line['long_accel'])
        self.assertFalse(df.gps_sync[8])

    def test_import_at1a_fill_nans(self):
        df = gi.read_at1a(os.path.abspath('tests/sample_gravity.csv'))
        self.assertEqual(df.shape, (10, 26))

        fields = ['gravity', 'long_accel', 'cross', 'beam', 'temp', 'status', 'pressure', 'Etemp', 'GPSweek', 'GPSweekseconds']
        # Test and verify an arbitrary line of data against the same line in the pandas DataFrame
        line5 = [10061.171360, -0.026226, -0.094891, -0.093803, 62.253987, 21061, 39.690004, 52.263138, 1959, 219697.800]
        sample_line = dict(zip(fields, line5))

        self.assertEqual(df.gravity[5], sample_line['gravity'])
        self.assertEqual(df.long_accel[5], sample_line['long_accel'])
        self.assertTrue(df.iloc[[2]].isnull().values.all())

    def test_import_at1a_interp(self):
        df = gi.read_at1a(os.path.abspath('tests/sample_gravity.csv'), interp=True)
        self.assertEqual(df.shape, (10, 26))

        # check whether NaNs were interpolated for numeric type fields
        self.assertTrue(df.iloc[[2]].notnull().values.any())

    def test_import_zls(self):
        df = gi.read_zls(os.path.abspath('tests/sample_zls'))
        self.assertEqual(df.shape, (10800, 16))

        line21 = ['FLIGHT3', 12754.71, 12747.7, 0.3, -375.8, -1.0, 0.0, -14.0, 5.0, -2.0, 57.0, 4.0, 128.0, -15.0, 'FFFFFF', 34.0]
        self.assertEqual(df.iloc[[20]].values.tolist()[0], line21)

    def test_import_zls_times(self):
        ok_begin_time = datetime.datetime(2015, 11, 12, hour=0, minute=30, second=0)
        ok_end_time = datetime.datetime(2015, 11, 12, hour=2, minute=30, second=0)
        df = gi.read_zls(os.path.abspath('tests/sample_zls'),
                         begin_time=ok_begin_time,
                         end_time=ok_end_time)

        self.assertTrue(df.index[0] == ok_begin_time)
        self.assertTrue(df.index[-1] == ok_end_time)

        oob_begin_time = datetime.datetime(2015, 11, 11, hour=23, minute=0, second=0)
        with self.assertRaises(ValueError):
            df = gi.read_zls(os.path.abspath('tests/sample_zls'), begin_time=oob_begin_time)

        oob_end_time = datetime.datetime(2015, 11, 12, hour=3, minute=0, second=0)
        with self.assertRaises(ValueError):
            df = gi.read_zls(os.path.abspath('tests/sample_zls'), end_time=oob_end_time)

        with self.assertRaises(ValueError):
            df = gi.read_zls(os.path.abspath('tests/sample_zls'),
                             begin_time=ok_begin_time,
                             end_time=oob_begin_time)
