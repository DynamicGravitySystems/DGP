# coding: utf-8

import unittest
import tempfile
import uuid
import json
from pathlib import Path

from pandas import DataFrame

from .context import dgp
import dgp.lib.datamanager as dm


class TestDataManager(unittest.TestCase):

    def setUp(self):
        data = {'Col1': ['c1-1', 'c1-2', 'c1-3'], 'Col2': ['c2-1', 'c2-2',
                                                           'c2-3']}
        self.test_frame = DataFrame.from_dict(data)

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
        self.assertIsInstance(mgr, dm._DataManager)

    def test_dm_save_hdf(self):
        mgr = dm.get_manager()
        self.assertTrue(mgr.init)

        res = mgr.save_data('hdf5', self.test_frame)
        loaded = mgr.load_data(res)
        self.assertTrue(self.test_frame.equals(loaded))
        # print(mgr._registry)

    @unittest.skip
    def test_dm_double_init(self):
        td2 = Path(tempfile.gettempdir()).joinpath(str(uuid.uuid4()))
        dm2 = dm._DataManager(td2)

    def test_registry(self):
        reg_tmp = Path(tempfile.gettempdir()).joinpath(str(uuid.uuid4()))
        reg_tmp.mkdir(parents=True)
        reg = dm._Registry(reg_tmp)
        # print(reg.registry)
