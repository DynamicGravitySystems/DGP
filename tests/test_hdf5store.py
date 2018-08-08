# -*- coding: utf-8 -*-

from datetime import datetime
from pathlib import Path

import pytest
from pandas import DataFrame

from dgp.core import DataType
from dgp.core.models.flight import Flight
from dgp.core.models.datafile import DataFile
from dgp.core.hdf5_manager import HDF5Manager

HDF5_FILE = "test.hdf5"


def test_datastore_save_load(gravdata: DataFrame, hdf5file: Path):
    flt = Flight('Test-Flight')
    datafile = DataFile(DataType.GRAVITY, datetime.now(), Path('tests/test.dat'))
    assert HDF5Manager.save_data(gravdata, datafile, path=hdf5file)
    loaded = HDF5Manager.load_data(datafile, path=hdf5file)
    assert gravdata.equals(loaded)

    # Test loading from file (clear cache)
    HDF5Manager.clear_cache()
    loaded_nocache = HDF5Manager.load_data(datafile, path=hdf5file)
    assert gravdata.equals(loaded_nocache)

    HDF5Manager.clear_cache()
    with pytest.raises(FileNotFoundError):
        HDF5Manager.load_data(datafile, path=Path('.nonexistent.hdf5'))

    empty_datafile = DataFile(DataType.TRAJECTORY, datetime.now(),
                              Path('tests/test.dat'))
    with pytest.raises(KeyError):
        HDF5Manager.load_data(empty_datafile, path=hdf5file)


def test_ds_metadata(gravdata: DataFrame, hdf5file: Path):
    flt = Flight('TestMetadataFlight')
    datafile = DataFile(DataType.GRAVITY, datetime.now(), source_path=Path('./test.dat'))
    empty_datafile = DataFile(DataType.TRAJECTORY, datetime.now(),
                              Path('tests/test.dat'))
    HDF5Manager.save_data(gravdata, datafile, path=hdf5file)

    attr_key = 'test_attr'
    attr_value = {'a': 'complex', 'v': 'value'}

    # Assert True result first
    assert HDF5Manager._set_node_attr(datafile.nodepath, attr_key, attr_value, hdf5file)
    # Validate value was stored, and can be retrieved
    result = HDF5Manager._get_node_attr(datafile.nodepath, attr_key, hdf5file)
    assert attr_value == result

    # Test retrieval of keys for a specified node
    assert attr_key in HDF5Manager.list_node_attrs(datafile.nodepath, hdf5file)

    with pytest.raises(KeyError):
        HDF5Manager._set_node_attr('/invalid/node/path', attr_key, attr_value,
                                   hdf5file)

    with pytest.raises(KeyError):
        HDF5Manager.list_node_attrs(empty_datafile.nodepath, hdf5file)

    assert HDF5Manager._get_node_attr(empty_datafile.nodepath, 'test_attr',
                                      hdf5file) is None
