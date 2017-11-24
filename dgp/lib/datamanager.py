# coding: utf-8

import logging
import uuid
import json
from pathlib import Path
from typing import Union

from pandas import HDFStore, DataFrame, Series

from dgp.lib.etc import gen_uuid

"""
Scratchpad: What should DataManager do?
All items should have an accompanying UID for reference/retrieval.

Should be initialized from Project Object

1. Store a DataFrame on the file system.
2. Retrieve a DataFrame from the file system.
2a. Store/retrieve metadata on other data objects.
2b. Cache any loaded data for the current session (up to a limit?)
3. Store an arbitrary dictionary.
4. Track original file location of any imported files.


What resource silos could we have?
HDF5
CSV/File
Serialized/Pickled objects
JSON
Backup files/archives (.zip/.tgz)

"""

__all__ = ['init', 'get_manager']

manager = None


class DataManager:
    """Do not instantiate this class directly. Call the module init() method"""
    _baseregister = {
        'version': 1,
        'dtypes': ['hdf5', 'json', 'csv'],
        'dfiles': {'hdf5': '',
                   'json': '',
                   'csv': ''}
    }

    def __init__(self, root_path):
        self.log = logging.getLogger(__name__)
        self.dir = Path(root_path)
        if not self.dir.exists():
            self.dir.mkdir(parents=True)
        self.reg_path = self.dir.joinpath('registry.json')
        self.reg = self._load_registry()
        self.init = True
        self._cache = {}
        self.log.debug("DataManager class initialized.")
        self._save_registry()

    def _load_registry(self):
        self.log.debug("Loading DataManager registry from {}".format(
            self.reg_path))
        if not self.reg_path.exists():
            print("No registry JSON exists.")
            return self._baseregister

        with self.reg_path.open(mode='r') as fd:
            return json.load(fd)

    def _save_registry(self):
        self.log.debug("Saving DataManager registry to: {}".format(
            str(self.reg_path)))
        with self.reg_path.open(mode='w') as fd:
            json.dump(self.reg, fd, indent=4)

    def save_data(self, dtype, data) -> str:
        fpath = self.reg['dfiles'][dtype]  # type: str
        if fpath == '' or fpath is None:
            fuid = uuid.uuid4().__str__()
            fname = '{uid}.{dtype}'.format(uid=fuid, dtype=dtype)
            fpath = str(self.dir.joinpath(fname))
            self.reg['dfiles'][dtype] = fpath

        with HDFStore(fpath) as hdf:
            duid = gen_uuid('dat')
            hdf.put('data/{}'.format(duid), data, format='fixed',
                    data_columns=True)
            # TODO: Map data uid to fuid in registry?
            # Would enable lookup by UID only without knowing dtype
        self._save_registry()
        self._cache[duid] = data
        return duid

    def load_data(self, dtype, uid):
        if uid in self._cache:
            self.log.debug("Returning data from in-memory cache.")
            return self._cache[uid]
        fpath = self.reg['dfiles'][dtype]
        print(fpath)
        if dtype == 'hdf5':
            with HDFStore(str(fpath)) as hdf:
                key = 'data/{uid}'.format(uid=uid)
                data = hdf.get(key)
            self._cache[uid] = data
            self.log.debug("Loading data from HDFStore on disk.")
            return data


def init(path: Path):
    global manager
    if manager is not None and manager.init:
        return False
    manager = DataManager(path)
    return True


def get_manager() -> Union[DataManager, None]:
    if manager is not None:
        return manager
    raise ValueError("DataManager has not been initialized.")