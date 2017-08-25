# coding: utf-8

import os
import unittest
import pandas as pd

from .context import dgp
from dgp.lib import gravity_ingestor as gi


class TestGravityIngestor(unittest.TestCase):

    def test_import_at1a(self):
        df = gi.read_at1a(os.path.abspath('tests/sample_gravity.csv'))
        self.assertEqual(df.shape, (10, 10))

        fields = ['gravity', 'long', 'cross', 'beam', 'temp', 'status', 'pressure', 'Etemp', 'GPSweek', 'GPSweekseconds']
        # Test and verify an arbitrary line of data against the same line in the pandas DataFrame
        line5 = [10061.171360, -0.026226, -0.094891, -0.093803, 62.253987, 21061, 39.690004, 52.263138, 1959, 219697.800]
        sample_line = dict(zip(fields, line5))

        self.assertEqual(df.gravity[5], sample_line['gravity'])
        self.assertEqual(df.long[5], sample_line['long'])
        self.assertTrue(df.iloc[[2]].isnull().all)
        print(df[['gravity', 'long', 'cross']])
