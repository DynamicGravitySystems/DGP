# coding: utf-8

import os
import unittest
import numpy as np

from .context import  dgp
import dgp.lib.eotvos as eotvos
import dgp.lib.trajectory_ingestor as ti


class TestEotvos(unittest.TestCase):
    def setUp(self):
        pass

    def test_derivative(self):
        pass

    def test_eotvos(self):
        gps_fields = ['mdy', 'hms', 'lat', 'long', 'ell_ht', 'ortho_ht', 'num_stats', 'pdop']
        data = ti.import_trajectory('tests/sample_data/sample_eotvos.csv', columns=gps_fields, skiprows=1,
                                    timeformat='hms')

        lat = data['lat']
        lon = data['long']
        ht = data['ell_ht']
        rate = 0.1

        E, r2dot, w2xrdot, wdotxr, wxwxr, wexwexr = eotvos.calc_eotvos(lat, lon, ht, rate)
