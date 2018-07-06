# -*- coding: utf-8 -*-

import uuid
from datetime import datetime
from pathlib import Path

import pytest
from pandas import DataFrame

from dgp.core.models.flight import Flight
from dgp.core.models.data import DataFile
from dgp.core.hdf5_manager import HDF5Manager, HDF5_NAME
# from .context import dgp

HDF5_FILE = "test.hdf5"

class TestDataManager:

    # @pytest.fixture(scope='session')
    # def temp_dir(self) -> Path:
    #     return Path(tempfile.gettempdir()).joinpath(str(uuid.uuid4()))

    # @pytest.fixture(scope='session')
    # def store(self, temp_dir: Path) -> HDF5Manager:
    #     hdf = HDF5Manager(temp_dir, mkdir=True)
    #     return hdf

    @pytest.fixture
    def test_df(self):
        data = {'Col1': ['c1-1', 'c1-2', 'c1-3'], 'Col2': ['c2-1', 'c2-2',
                                                           'c2-3']}
        return DataFrame.from_dict(data)

    def test_datastore_save(self, test_df, tmpdir):
        flt = Flight('Test-Flight')
        file = DataFile('gravity', datetime.now(), Path('./test.dat'), parent=flt)
        path = Path(tmpdir).joinpath(HDF5_FILE)
        assert HDF5Manager.save_data(test_df, file, path=path)
        loaded = HDF5Manager.load_data(file, path=path)
        assert test_df.equals(loaded)

    def test_ds_metadata(self, test_df, tmpdir):
        path = Path(tmpdir).joinpath(HDF5_FILE)
        flt = Flight('TestMetadataFlight')
        file = DataFile('gravity', datetime.now(), source_path=Path('./test.dat'), parent=flt)
        HDF5Manager.save_data(test_df, file, path=path)

        attr_key = 'test_attr'
        attr_value = {'a': 'complex', 'v': 'value'}

        # Assert True result first
        assert HDF5Manager._set_node_attr(file.hdfpath, attr_key, attr_value, path)
        # Validate value was stored, and can be retrieved
        result = HDF5Manager._get_node_attr(file.hdfpath, attr_key, path)
        assert attr_value == result

        # Test retrieval of keys for a specified node
        assert attr_key in HDF5Manager.get_node_attrs(file.hdfpath, path)

        with pytest.raises(KeyError):
            HDF5Manager._set_node_attr('/invalid/node/path', attr_key, attr_value, path)
