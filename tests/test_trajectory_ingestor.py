# coding: utf-8

import os
import unittest
import pandas as pd
import numpy as np

from dgp.lib import trajectory_ingestor as ti


class TestTrajectoryIngestor(unittest.TestCase):

    def test_import_trajectory(self):
        fields = ['mdy', 'hms', 'lat', 'long', 'ell_ht', 'ortho_ht', 'num_sats', 'pdop']
        df = ti.import_trajectory(os.path.abspath('tests/sample_trajectory.txt'),
                                  columns=fields, skiprows=1, timeformat='hms')

        # Test and verify an arbitrary line of data against the same line in the pandas DataFrame
        line11 = ['3/22/2017', '9:59:00.20', 76.5350241071, -68.7218956324, 65.898, 82.778, 11, 2.00]
        sample_line = dict(zip(fields, line11))

        np.testing.assert_almost_equal(df.lat[10], sample_line['lat'], decimal=10)
        np.testing.assert_almost_equal(df.long[10], sample_line['long'], decimal=10)

        # check whether the gap was filled with NaNs
        self.assertTrue(df.iloc[[2]].isnull().values.all())


    def test_import_trajectory_interp_nans(self):
        fields = ['mdy', 'hms', 'lat', 'long', 'ell_ht', 'ortho_ht', 'num_sats', 'pdop']
        df = ti.import_trajectory(os.path.abspath('tests/sample_trajectory.txt'),
                                  columns=fields, skiprows=1, timeformat='hms',
                                  interp=True)

        # Test and verify an arbitrary line of data against the same line in the pandas DataFrame
        line11 = ['3/22/2017', '9:59:00.20', 76.5350241071, -68.7218956324, 65.898, 82.778, 11, 2.00]
        sample_line = dict(zip(fields, line11))

        np.testing.assert_almost_equal(df.lat[10], sample_line['lat'], decimal=10)
        np.testing.assert_almost_equal(df.long[10], sample_line['long'], decimal=10)
        numeric = df.select_dtypes(include=[np.number])

        # check whether NaNs were interpolated for numeric type fields
        self.assertTrue(numeric.iloc[[2]].notnull().values.all())


    def test_import_trajectory_fields(self):
        # test number of fields in data greater than number of fields named
        fields = ['mdy', 'hms', 'lat', 'long', 'ell_ht']
        df = ti.import_trajectory(os.path.abspath('tests/sample_trajectory.txt'),
                                  columns=fields, skiprows=1, timeformat='hms')

        columns = [x for x in fields if x is not None]
        np.testing.assert_array_equal(df.columns, columns[2:])

        # test fields in the middle are dropped
        fields = ['mdy', 'hms', 'lat', 'long', 'ell_ht', None, 'num_sats', 'pdop']
        df = ti.import_trajectory(os.path.abspath('tests/sample_trajectory.txt'),
                                  columns=fields, skiprows=1, timeformat='hms')

        columns = [x for x in fields if x is not None]
        np.testing.assert_array_equal(df.columns, columns[2:])


    def test_import_trajectory_time_formats(self):
        fields1 = ['mdy', 'hms', 'lat', 'long', 'ell_ht', 'ortho_ht', 'num_sats', 'pdop']
        df1 = ti.import_trajectory(os.path.abspath('tests/sample_trajectory.txt'),
            columns=fields1, skiprows=1, timeformat='hms')

        fields2 = ['week', 'sow', 'lat', 'long', 'ell_ht', 'ortho_ht', 'num_sats', 'pdop']
        df2 = ti.import_trajectory(os.path.abspath('tests/sample_trajectory_week-sow.txt'),
            columns=fields2, skiprows=1, timeformat='sow')

        self.assertTrue(df1.index.equals(df2.index))
        

    def test_import_trajectory_default_fields(self):
        df1 = ti.import_trajectory(os.path.abspath('tests/sample_trajectory.txt'),
                                  skiprows=1, timeformat='hms')

        df2 = ti.import_trajectory(os.path.abspath('tests/sample_trajectory_week-sow.txt'),
                                  skiprows=1, timeformat='sow')

        self.assertTrue(df1.equals(df2))
