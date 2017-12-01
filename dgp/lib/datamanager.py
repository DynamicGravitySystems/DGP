# coding: utf-8

import logging
import json
from pathlib import Path
from typing import Union

from pandas import HDFStore, DataFrame

from dgp.lib.etc import gen_uuid

"""
Dynamic Gravity Processor (DGP) :: lib/datamanager.py
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

What resource silos could we have?
HDF5
CSV/File
Serialized/Pickled objects
JSON
Backup files/archives (.zip/.tgz)

"""

__all__ = ['init', 'get_manager', 'HDF5', 'JSON', 'CSV']

REGISTRY_NAME = 'dmreg.json'

# Define Data Types
HDF5 = 'hdf5'
JSON = 'json'
CSV = 'csv'

_manager = None


class _Registry:
    """
    A JSON utility class that allows us to read/write from the JSON file
    with a context manager. The context manager handles automatic saving and
    loading of the JSON registry file.
    """
    __emtpy = {
        'version': 1,
        'datamap': {}   # data_uid -> data_type
    }

    def __init__(self, path: Path):
        self.__base_path = Path(path)
        self.__path = self.__base_path.joinpath(REGISTRY_NAME)
        self.__registry = None

    def __load(self) -> None:
        """Load the registry from __path, create and dump if it doesn't exist"""
        try:
            with self.__path.open('r') as fd:
                self.__registry = json.load(fd)
        except FileNotFoundError:
            self.__registry = self.__emtpy.copy()
            self.__save()

    def __save(self) -> None:
        """Save __registry to __path as JSON"""
        with self.__path.open('w') as fd:
            json.dump(self.__registry, fd, indent=4)

    def get_hdfpath(self, touch=True) -> Path:
        """
        Return the stored HDF5 file path, or create a new one if it
        doesn't exist.

        Notes
        -----
        The newly generated hdf file name will be created if touch=True,
        else the file path must be written to in order to create it.
        """
        if HDF5 in self.registry:
            return self.__base_path.joinpath(self.registry[HDF5])

        # Create the HDF5 path if it doesnt exist
        with self as reg:
            fname = gen_uuid('repo_') + '.hdf5'
            reg.setdefault(HDF5, fname)
        path = self.__base_path.joinpath(fname)
        if touch:
            path.touch()
        return path

    def get_type(self, uid) -> Path:
        """Return the data type of data represented by UID"""
        return self.registry['datamap'][uid]

    @property
    def registry(self) -> dict:
        """Return internal registry, loading it from file if None"""
        if self.__registry is None:
            self.__load()
        return self.__registry

    def __getitem__(self, item) -> dict:
        return self.registry[item]

    def __enter__(self) -> dict:
        """Context manager entry point, return reference to registry dict"""
        return self.registry

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit, save/dump any changes to registry to file"""
        self.__save()


class _DataManager:
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

    def __new__(cls, *args, **kwargs):
        """The utility of this is questionable. Idea is to ensure this class
        is a singleton"""
        global _manager
        if _manager is not None:
            return _manager
        _manager = super().__new__(cls)
        return _manager

    def __init__(self, root_path):
        self.log = logging.getLogger(__name__)
        self.dir = Path(root_path)
        if not self.dir.exists():
            self.dir.mkdir(parents=True)

        # Initialize the JSON Registry
        self._registry = _Registry(self.dir)
        self._cache = {}
        self.init = True
        self.log.debug("DataManager initialized.")

    def save_data(self, dtype, data) -> str:
        """
        Save data to a repository for dtype information.
        Data is added to the local cache, keyed by its generated UID.
        The generated UID is passed back to the caller for later reference.
        This function serves as a dispatch mechanism for different data types.
        e.g. To dump a pandas DataFrame into an HDF5 store:
        >>> df = DataFrame()
        >>> uid = get_manager().save_data(HDF5, df)
        The DataFrame can later be loaded by calling load_data, e.g.
        >>> df = get_manager().load_data(uid)

        Parameters
        ----------
        dtype: str
            Data type, determines how/where data is saved.
            Options: HDF5, JSON, CSV
        data: Union[DataFrame, Series, dict, list, str]
            Data object to be stored on disk via specified format.

        Returns
        -------
        str:
            Generated UID assigned to data object saved.
        """
        if dtype == HDF5:
            uid = self._save_hdf5(data)
            self._cache[uid] = data
            return uid

    def _save_hdf5(self, data, uid=None):
        """
        Saves data to the managed HDF5 repository.
        Parameters
        ----------
        data: Union[DataFrame, Series]
        uid: str
            Optional UID to assign to the data - if None specified a new UID
            will be generated.

        Returns
        -------
        str:
            Returns the UID of the data saved to the HDF5 repo.
        """
        hdf_path = self._registry.get_hdfpath()
        if uid is None:
            uid = gen_uuid('data_')
        with HDFStore(str(hdf_path)) as hdf, self._registry as reg:
            print("Writing to hdfstore: ", hdf_path)
            hdf.put(uid, data, format='fixed', data_columns=True)
            reg['datamap'].update({uid: HDF5})
        return uid

    def load_data(self, uid):
        """
        Load data from a managed repository by UID
        This public method is a dispatch mechanism that calls the relevant
        loader based on the data type of the data represented by UID.
        This method will first check the local cache for UID, and if the key
        is not located, will attempt to load it from its location stored in
        the registry.
        Parameters
        ----------
        uid: str
            UID of stored date to retrieve.

        Returns
        -------
        Union[DataFrame, Series, dict]
            Data retrieved from store.
        """
        if uid in self._cache:
            self.log.info("Loading data {} from cache.".format(uid))
            return self._cache[uid]

        dtype = self._registry.get_type(uid)
        if dtype == HDF5:
            data = self._load_hdf5(uid)
            self._cache[uid] = data
            return data

    def _load_hdf5(self, uid):
        self.log.warning("Loading HDF5 data from on-disk storage.")
        hdf_path = self._registry.get_hdfpath()
        with HDFStore(str(hdf_path)) as hdf:
            data = hdf.get(uid)
        return data


def init(path: Path):
    """
    Initialize the DataManager with specified base path. All data and
    metadata will be stored within this path.
    """
    global _manager
    if _manager is not None and _manager.init:
        return False
    _manager = _DataManager(path)
    return True


def get_manager() -> Union[_DataManager, None]:
    if _manager is not None:
        return _manager
    raise ValueError("DataManager has not been initialized. Call "
                     "datamanager.init(path)")
