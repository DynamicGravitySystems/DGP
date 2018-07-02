# -*- coding: utf-8 -*-

import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from pandas import DataFrame

from core.models.flight import Flight
from .context import dgp
from dgp.core.models.data import DataFile
from dgp.core.oid import OID
from dgp.core.controllers.hdf5_controller import HDFController, HDF5_NAME


class TestDataManager:

    @pytest.fixture(scope='session')
    def temp_dir(self) -> Path:
        return Path(tempfile.gettempdir()).joinpath(str(uuid.uuid4()))

    @pytest.fixture(scope='session')
    def store(self, temp_dir: Path) -> HDFController:
        hdf = HDFController(temp_dir, mkdir=True)
        return hdf

    @pytest.fixture
    def test_df(self):
        data = {'Col1': ['c1-1', 'c1-2', 'c1-3'], 'Col2': ['c2-1', 'c2-2',
                                                           'c2-3']}
        return DataFrame.from_dict(data)

    def test_datastore_init(self, store, temp_dir):
        assert isinstance(store, HDFController)
        assert store.dir == temp_dir
        assert store.hdf5path == temp_dir.joinpath(HDF5_NAME)

    def test_datastore_save(self, store, test_df):
        flt = Flight('Test-Flight')
        file = DataFile('gravity', datetime.now(), Path('./test.dat'), parent=flt)
        assert store.save_data(test_df, file)
        loaded = store.load_data(file)
        assert test_df.equals(loaded)

    def test_ds_metadata(self, store: HDFController, test_df):
        flt = Flight('TestMetadataFlight')
        file = DataFile('gravity', datetime.now(), source_path=Path('./test.dat'), parent=flt)
        store.save_data(test_df, file)

        attr_key = 'test_attr'
        attr_value = {'a': 'complex', 'v': 'value'}

        # Assert True result first
        assert store._set_node_attr(file.hdfpath, attr_key, attr_value)
        # Validate value was stored, and can be retrieved
        result = store._get_node_attr(file.hdfpath, attr_key)
        assert attr_value == result

        # Test retrieval of keys for a specified node
        assert attr_key in store.get_node_attrs(file.hdfpath)

        with pytest.raises(KeyError):
            store._set_node_attr('/invalid/node/path', attr_key, attr_value)
