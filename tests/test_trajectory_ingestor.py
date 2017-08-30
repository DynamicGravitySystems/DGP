# coding: utf-8

import os
import unittest
import pandas as pd
import numpy as np

from .context import dgp
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
        self.assertTrue(df.iloc[[2]].isnull().all)
        # print(df[['lat', 'long', 'ell_ht']])

    def test_import_trajectory_fields(self):
        # test number of fields in data greater than number of fields named
        fields = ['mdy', 'hms', 'lat', 'long', 'ell_ht']
        df = ti.import_trajectory(os.path.abspath('tests/sample_trajectory.txt'),
                                  columns=fields, skiprows=1, timeformat='hms')

        columns = [x for x in fields if x is not None]
        np.testing.assert_array_equal(df.columns, columns)
        # print(df.columns)

        # test fields in the middle are dropped
        fields = ['mdy', 'hms', 'lat', 'long', 'ell_ht', None, 'num_sats', 'pdop']
        df = ti.import_trajectory(os.path.abspath('tests/sample_trajectory.txt'),
                                  columns=fields, skiprows=1, timeformat='hms')

        columns = [x for x in fields if x is not None]
        np.testing.assert_array_equal(df.columns, columns)
        # print(df.columns)

    def test_import_trajectory_time_formats(self):
        fields1 = ['mdy', 'hms', 'lat', 'long', 'ell_ht', 'ortho_ht', 'num_sats', 'pdop']
        df1 = ti.import_trajectory(os.path.abspath('tests/sample_trajectory.txt'),
            columns=fields1, skiprows=1, timeformat='hms')

        fields2 = ['week', 'sow', 'lat', 'long', 'ell_ht', 'ortho_ht', 'num_sats', 'pdop']
        df2 = ti.import_trajectory(os.path.abspath('tests/sample_trajectory_week-sow.txt'),
            columns=fields2, skiprows=1, timeformat='sow')

        self.assertTrue(df1.index.equals(df2.index))
