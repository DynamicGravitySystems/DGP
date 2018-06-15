# coding: utf-8

from .context import dgp

import logging
import unittest
from pathlib import Path

import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtTest as QtTest
from pandas import DataFrame

import dgp.gui.loader as loader
import dgp.lib.enums as enums
import dgp.lib.gravity_ingestor as gi
import dgp.lib.trajectory_ingestor as ti
import dgp.lib.types as types


class TestLoader(unittest.TestCase):
    """Test the Threaded file loader class in dgp.gui.loader"""

    def setUp(self):
        self.app = QtWidgets.QApplication([])
        self.grav_path = Path('tests/sample_gravity.csv')
        self.gps_path = Path('tests/sample_trajectory.txt')
        self._result = {}
        # Disable logging output expected from thread testing (cannot be caught)
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def sig_emitted(self, key, value):
        self._result[key] = value

    def test_load_gravity(self):
        grav_df = gi.read_at1a(str(self.grav_path))
        self.assertEqual((10, 26), grav_df.shape)

        ld = loader.LoaderThread(
            loader.GRAVITY_INGESTORS[loader.GravityTypes.AT1A], self.grav_path,
            loader.DataTypes.GRAVITY)
        ld.error.connect(lambda x: self.sig_emitted('err', x))
        ld.result.connect(lambda x: self.sig_emitted('data', x))
        ld.start()
        ld.wait()

        # Process signal events
        self.app.processEvents()

        self.assertFalse(self._result['err'][0])
        self.assertIsInstance(self._result['data'], DataFrame)

        self.assertTrue(grav_df.equals(self._result['data']))

        # Test Error Handling (pass GPS data to cause a ValueError)
        ld_err = loader.LoaderThread.from_gravity(None, self.gps_path)
        ld_err.error.connect(lambda x: self.sig_emitted('err2', x))
        ld_err.start()
        ld_err.wait()
        self.app.processEvents()

        err, exc = self._result['err2']
        self.assertTrue(err)
        self.assertIsInstance(exc, ValueError)

    def test_load_trajectory(self):
        cols = ['mdy', 'hms', 'lat', 'long', 'ell_ht', 'ortho_ht', 'num_sats',
                'pdop']
        gps_df = ti.import_trajectory(self.gps_path, columns=cols,
                                      skiprows=1, timeformat='hms')

        ld = loader.LoaderThread.from_gps(None, self.gps_path,
                                          enums.GPSFields.hms, columns=cols,
                                          skiprows=1)
        ld.error.connect(lambda x: self.sig_emitted('gps_err', x))
        ld.result.connect(lambda x: self.sig_emitted('gps_data', x))
        ld.start()
        ld.wait()
        self.app.processEvents()

        self.assertTrue(gps_df.equals(self._result['gps_data']))
