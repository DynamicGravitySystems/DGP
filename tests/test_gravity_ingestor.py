# coding: utf-8

import os
import unittest

from .context import dgp
from dgp.lib import gravity_ingestor as gi


class TestGravityIngestor(unittest.TestCase):

    def test_convert_gps_time(self):
        gpsweek = 1959
        gpsweeksecond = 219698.000
        result = 1500987698  # 2017-07-25 13:01:38+00:00
        test_res = gi.convert_gps_time(gpsweek, gpsweeksecond)
        self.assertEqual(result, test_res)

    def test_import_at1m(self):
        os.chdir('tests')
        df = gi.read_at1m(os.path.abspath('./sample.csv'))
        self.assertEqual(df.shape, (10, 9))

        fields = ['gravity', 'long', 'cross', 'beam', 'temp', 'status', 'pressure', 'Etemp', 'GPSweek', 'GPSweekseconds']
        # Test and verify an arbitrary line of data against the same line in the pandas DataFrame
        line5 = [10061.171360, -0.026226, -0.094891, -0.093803, 62.253987, 21061, 39.690004, 52.263138, 1959, 219697.800]
        sample_line = dict(zip(fields, line5))

        self.assertEqual(df.gravity[5], sample_line['gravity'])
        self.assertEqual(df.long[5], sample_line['long'])
        print(df[['gravity', 'long', 'cross']])

