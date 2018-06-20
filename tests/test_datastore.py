# -*- coding: utf-8 -*-

import tempfile
import uuid
from pathlib import Path

import pytest
from pandas import DataFrame

# from .context import dgp
import dgp.lib.datastore as ds


class TestDataManager:

    @pytest.fixture(scope='session')
    def temp_dir(self):
        return Path(tempfile.gettempdir()).joinpath(str(uuid.uuid4()))

    @pytest.fixture(scope='session')
    def store(self, temp_dir) -> ds._DataStore:
        ds.init(temp_dir)
        return ds.get_datastore()

    @pytest.fixture
    def test_df(self):
        data = {'Col1': ['c1-1', 'c1-2', 'c1-3'], 'Col2': ['c2-1', 'c2-2',
                                                           'c2-3']}
        return DataFrame.from_dict(data)

    def test_datastore_init(self, store, temp_dir):
        store = ds.get_datastore()
        assert isinstance(store, ds._DataStore)
        assert store.dir == temp_dir
        assert store._path == temp_dir.joinpath(ds.HDF5_NAME)

    def test_datastore_save(self, store, test_df):
        assert store.initialized

        fltid = uuid.uuid4()

        res = store.save_data(test_df, fltid, 'gravity')
        loaded = store.load_data(fltid, 'gravity', res)
        assert test_df.equals(loaded)

    def test_ds_metadata(self, store: ds._DataStore, test_df):
        fltid = uuid.uuid4()
        grpid = 'gravity'
        uid = uuid.uuid4()

        node_path = store._get_path(fltid, grpid, uid)
        store.save_data(test_df, fltid, grpid, uid)

        attr_key = 'test_attr'
        attr_value = {'a': 'complex', 'v': 'value'}

        # Assert True result first
        assert store._set_node_attr(node_path, attr_key, attr_value)
        # Validate value was stored, and can be retrieved
        result = store._get_node_attr(node_path, attr_key)
        assert attr_value == result

        # Test retrieval of keys for a specified node
        assert attr_key in store.get_node_attrs(node_path)

        with pytest.raises(KeyError):
            store._set_node_attr('/invalid/node/path', attr_key, attr_value)
