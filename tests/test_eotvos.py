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

    @unittest.skip("Not implemented.")
    def test_derivative(self):
        """Test derivation function against table of values calculated in MATLAB"""
        dlat = []
        ddlat = []
        dlon = []
        ddlon = []
        dht = []
        ddht = []
        # with sample_dir.joinpath('result_derivative.csv').open() as fd:
        #     reader = csv.DictReader(fd)
        #     dlat = list(map(lambda line: dlat.append(line['dlat']), reader))

    def test_eotvos(self):
        """Test Eotvos function against corrections generated with MATLAB program."""
        # Ensure gps_fields are ordered correctly relative to test file
        gps_fields = ['mdy', 'hms', 'lat', 'long', 'ortho_ht', 'ell_ht', 'num_stats', 'pdop']
        data = ti.import_trajectory('tests/sample_data/eotvos_short_input.txt', columns=gps_fields, skiprows=1,
                                    timeformat='hms')

        result_eotvos = []
        with sample_dir.joinpath('eotvos_short_result.csv').open() as fd:
            test_data = csv.DictReader(fd)
            # print(test_data.fieldnames)
            for line in test_data:
                result_eotvos.append(float(line['Eotvos_full']))
        lat = data['lat'].values
        lon = data['long'].values
        ht = data['ell_ht'].values
        rate = 10

        eotvos_a, *_ = eotvos.calc_eotvos(lat, lon, ht, rate, derivation_func=eotvos.derivative)
        for i, value in enumerate(eotvos_a):
            try:
                self.assertAlmostEqual(value, result_eotvos[i], places=2)
            except AssertionError:
                print("Invalid assertion at data line: {}".format(i))
                raise AssertionError
