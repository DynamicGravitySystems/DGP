# coding: utf-8

import logging
import json
from pathlib import Path
from typing import Union

import tables
import tables.exceptions
from tables.attributeset import AttributeSet
from pandas import HDFStore, DataFrame

from dgp.lib.etc import gen_uuid

"""
Dynamic Gravity Processor (DGP) :: lib/datastore.py
License: Apache License V2

Work in Progress
Should be initialized from Project Object, to pass project base dir.

Requirements:
1. Store a DataFrame on the file system.
2. Retrieve a DataFrame from the file system.
2a. Store/retrieve metadata on other data objects.
2b. Cache any loaded data for the current session (up to a limit? e.g. LRU)
3. Store an arbitrary dictionary.
4. Track original file location of any imported files.

TODO: Re-focus the idea of this module.
Our PRIMARY goal is to provide a global interface to save/load data (and related meta-data)
from an HDF5 data file.
Other data storage types are not of concern at the moment (e.g. Exporting to CSV, JSON)
- those should be the purview of another specialized module (e.g. exports)


METADATA:

Might be able to use hf.get_node('path') then node._f_setattr('key', 'value') / node._f_getattr('attr')
for metadata storage

"""

__all__ = ['init', 'get_datastore', 'HDF5']

# Define Data Types
HDF5 = 'hdf5'
HDF5_NAME = 'dgpdata.hdf5'

_manager = None


class _DataStore:
    """
    Do not instantiate this class directly. Call the module init() method
    DataManager is designed to be a singleton class that is initialized and
    stored within the module level var 'manager', other modules can then
    request a reference to the instance via get_manager() and use the class
    to load and save data.
    This is similar in concept to the Python Logging
    module, where the user can call logging.getLogger() to retrieve a global
    root logger object.
    The DataManager will be responsible for most if not all data IO,
    providing a centralized interface to store, retrieve, and export data.
    To track the various data files that the DataManager manages, a JSON
    registry is maintained within the project/data directory. This JSON
    registry is updated and queried for relative file paths, and may also be
    used to store mappings of uid -> file for individual blocks of data.
    """
    _registry = None
    _init = False

    def __new__(cls, *args, **kwargs):
        global _manager
        if _manager is not None and isinstance(_manager, _DataStore):
            return _manager
        _manager = super().__new__(cls)
        return _manager

    def __init__(self, root_path):
        self.log = logging.getLogger(__name__)
        self.dir = Path(root_path)
        if not self.dir.exists():
            self.dir.mkdir(parents=True)
        # TODO: Consider searching by extension (.hdf5 .h5) for hdf5 datafile
        self._path = self.dir.joinpath(HDF5_NAME)

        self._cache = {}
        self._init = True
        self.log.debug("DataStore initialized.")

    @property
    def initialized(self):
        return self._init

    @property
    def hdf5path(self):
        return str(self._path)

    @hdf5path.setter
    def hdf5path(self, value):
        value = Path(value)
        if not value.exists():
            raise FileNotFoundError
        else:
            self._path = value

    @staticmethod
    def _get_path(flightid, grpid, uid):
        return '/'.join(map(str, ['', flightid, grpid, uid]))

    def save_data(self, data, flightid, grpid, uid=None, **kwargs) -> Union[str, None]:
        """
        Save a Pandas Series or DataFrame to the HDF5 Store
        Data is added to the local cache, keyed by its generated UID.
        The generated UID is passed back to the caller for later reference.
        This function serves as a dispatch mechanism for different data types.
        e.g. To dump a pandas DataFrame into an HDF5 store:
        >>> df = DataFrame()
        >>> uid = get_datastore().save_data(df)
        The DataFrame can later be loaded by calling load_data, e.g.
        >>> df = get_datastore().load_data(uid)

        Parameters
        ----------
        data: Union[DataFrame, Series]
            Data object to be stored on disk via specified format.
        flightid: String
        grpid: String
            Data group (Gravity/Trajectory etc)
        uid: String
        kwargs:
            Optional Metadata attributes to attach to the data node

        Returns
        -------
        str:
            Generated UID assigned to data object saved.
        """

        self._cache[uid] = data
        if uid is None:
            uid = gen_uuid('hdf5_')

        # Generate path as /{flight_uid}/{grp_id}/uid
        path = self._get_path(flightid, grpid, uid)

        with HDFStore(self.hdf5path) as hdf:
            try:
                hdf.put(path, data, format='fixed', data_columns=True)
            except:
                self.log.exception("Exception writing file to HDF5 store.")
                return None
            else:
                self.log.info("Wrote file to HDF5 store at node: %s", path)
                # TODO: Figure out how to embed meta-data in the HDF5 store
                # It's possible with the underlying PyTables interface, but need to investigate if possible with pandas
                # HDFStore interface

        return uid

    def load_data(self, flightid, grpid, uid):
        """
        Load data from a managed repository by UID
        This public method is a dispatch mechanism that calls the relevant
        loader based on the data type of the data represented by UID.
        This method will first check the local cache for UID, and if the key
        is not located, will load it from the HDF5 Data File.

        Parameters
        ----------
        flightid: String
        grpid: String
        uid: String
            UID of stored date to retrieve.

        Returns
        -------
        Union[DataFrame, Series, dict]
            Data retrieved from store.

        Raises
        ------
        KeyError
            If data key (/flightid/grpid/uid) does not exist
        """

        if uid in self._cache:
            self.log.info("Loading data {} from cache.".format(uid))
            return self._cache[uid]
        else:
            path = self._get_path(flightid, grpid, uid)
            self.log.debug("Loading data %s from hdf5 store.", path)

            with HDFStore(self.hdf5path) as hdf:
                data = hdf.get(path)

            # Cache the data
            self._cache[uid] = data
            return data

    # See https://www.pytables.org/usersguide/libref/file_class.html#tables.File.set_node_attr
    # For more details on setting/retrieving metadata from hdf5 file using pytables
    # Note that the _v_ and _f_ prefixes are meant for instance variables and public methods
    # within pytables - so the inspection warning can be safely ignored

    def get_node_attrs(self, path) -> list:
        with tables.open_file(self.hdf5path) as hdf:
            try:
                return hdf.get_node(path)._v_attrs._v_attrnames
            except tables.exceptions.NoSuchNodeError:
                raise ValueError("Specified path %s does not exist.", path)

    def _get_node_attr(self, path, attrname):
        with tables.open_file(self.hdf5path) as hdf:
            try:
                return hdf.get_node_attr(path, attrname)
            except AttributeError:
                return None

    def _set_node_attr(self, path, attrname, value):
        with tables.open_file(self.hdf5path, 'a') as hdf:
            try:
                hdf.set_node_attr(path, attrname, value)
            except tables.exceptions.NoSuchNodeError:
                self.log.error("Unable to set attribute on path: %s key does not exist.")
                raise KeyError("Node %s does not exist", path)
            else:
                return True


def init(path: Path):
    """
    Initialize the DataManager with specified base path. All data and
    metadata will be stored within this path.
    """
    global _manager
    if _manager is not None and _manager.initialized:
        return False
    _manager = _DataStore(path)
    return True


def get_datastore() -> Union[_DataStore, None]:
    if _manager is not None:
        return _manager
    raise ValueError("DataManager has not been initialized. Call "
                     "datamanager.init(path)")
