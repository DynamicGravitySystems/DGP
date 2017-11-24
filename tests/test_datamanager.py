# coding: utf-8

import unittest
import tempfile
import uuid
import json
from pathlib import Path

from pandas import DataFrame

import dgp.lib.datamanager as dm


class TestDataManager(unittest.TestCase):

    # with tempfile.NamedTemporaryFile() as tf:
    #     tf.write(b"This is not a directory")
    def setUp(self):
        data = {'Col1': ['c1-1', 'c1-2', 'c1-3'], 'Col2': ['c2-1', 'c2-2',
                                                           'c2-3']}
        self.test_frame = DataFrame.from_dict(data)
        self._baseregister = {
            'version': 1,
            'dtypes': ['hdf5', 'json', 'csv'],
            'dfiles': {'hdf5': '',
                       'json': '',
                       'csv': ''}
        }

    def tearDown(self):
        pass

    def test_dm_init(self):
        td = Path(tempfile.gettempdir()).joinpath(str(uuid.uuid4()))
        with self.assertRaises(ValueError):
            mgr = dm.get_manager()

        dm.init(td)
        self.assertTrue(td.exists())

        mgr = dm.get_manager()
        self.assertEqual(mgr.dir, td)
        self.assertIsInstance(mgr, dm.DataManager)
        self.assertDictEqual(mgr.reg, self._baseregister)

    def test_dm_save_hdf(self):
        mgr = dm.get_manager()
        self.assertTrue(mgr.init)

        res = mgr.save_data('hdf5', self.test_frame)
        loaded = mgr.load_data('hdf5', res)
        self.assertTrue(self.test_frame.equals(loaded))

    def test_dm_registry(self):
        mgr = dm.get_manager()

        uid = mgr.save_data('hdf5', self.test_frame)

        with mgr.reg_path.open(mode='r') as fd:
            reg = json.load(fd)
        print(reg)
