# coding: utf-8

import os
import unittest
import numpy as np
import csv

from .context import  dgp
from tests import sample_dir
import dgp.lib.eotvos as eotvos
import dgp.lib.trajectory_ingestor as ti


class TestEotvos(unittest.TestCase):
    """Test Eotvos correction calculation."""
    def setUp(self):
        pass

    def test_derivative(self):
        pass

    def test_eotvos(self):
        """Test Eotvos function against corrections generated with MATLAB program."""
        gps_fields = ['mdy', 'hms', 'lat', 'long', 'ell_ht', 'ortho_ht', 'num_stats', 'pdop']
        data = ti.import_trajectory('tests/sample_data/sample_eotvos_trajectory.csv', columns=gps_fields, skiprows=1,
                                    timeformat='hms')

        result_eotvos = []
        with sample_dir.joinpath('result_eotvos.csv').open() as fd:
            test_data = csv.DictReader(fd)
            for line in test_data:
                result_eotvos.append(line['eotvos'])

        lat = data['lat']
        lon = data['long']
        ht = data['ell_ht']
        rate = 0.1

        eotvos_a, r2dot, w2xrdot, wdotxr, wxwxr, wexwexr = eotvos.calc_eotvos(lat, lon, ht, rate)
        for i, value in enumerate(eotvos_a):
            self.assertEqual(value, test_data['eotvos'][i])
