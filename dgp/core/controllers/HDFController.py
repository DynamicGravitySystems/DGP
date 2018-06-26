# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from typing import Tuple
from uuid import uuid4

import tables
from pandas import HDFStore, DataFrame

__all__ = ['HDF5', 'HDFController']

# Define Data Types/Extensions
HDF5 = 'hdf5'
HDF5_NAME = 'dgpdata.hdf5'


class HDFController:
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
    providing a centralized interface to _store, retrieve, and export data.
    To track the various data files that the DataManager manages, a JSON
    registry is maintained within the project/data directory. This JSON
    registry is updated and queried for relative file paths, and may also be
    used to _store mappings of uid -> file for individual blocks of data.
    """

    def __init__(self, root_path, mkdir: bool = True):
        self.log = logging.getLogger(__name__)
        self.dir = Path(root_path)
        if not self.dir.exists() and mkdir:
            self.dir.mkdir(parents=True)
        # TODO: Consider searching by extension (.hdf5 .h5) for hdf5 datafile
        self._path = self.dir.joinpath(HDF5_NAME)
        self._path.touch(exist_ok=True)
        self._cache = {}
        self.log.debug("DataStore initialized.")

    @property
    def hdf5path(self) -> Path:
        return self._path

    @hdf5path.setter
    def hdf5path(self, value):
        value = Path(value)
        if not value.exists():
            raise FileNotFoundError
        else:
            self._path = value

    @staticmethod
    def join_path(flightid, grpid, uid):
        return '/'.join(map(str, ['', flightid, grpid, uid]))

    def save_data(self, data: DataFrame, flightid: str, grpid: str,
                  uid=None, **kwargs) -> Tuple[str, str, str, str]:
        """
        Save a Pandas Series or DataFrame to the HDF5 Store
        Data is added to the local cache, keyed by its generated UID.
        The generated UID is passed back to the caller for later reference.
        This function serves as a dispatch mechanism for different data types.
        e.g. To dump a pandas DataFrame into an HDF5 _store:
        >>> df = DataFrame()
        >>> uid = HDFController().save_data(df)
        The DataFrame can later be loaded by calling load_data, e.g.
        >>> df = HDFController().load_data(uid)

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

        if uid is None:
            uid = str(uuid4().hex)

        self._cache[uid] = data

        # Generate path as /{flight_uid}/{grp_id}/uid
        path = self.join_path(flightid, grpid, uid)

        with HDFStore(str(self.hdf5path)) as hdf:
            try:
                hdf.put(path, data, format='fixed', data_columns=True)
            except (IOError, FileNotFoundError, PermissionError):
                self.log.exception("Exception writing file to HDF5 _store.")
                raise
            else:
                self.log.info("Wrote file to HDF5 _store at node: %s", path)

        return flightid, grpid, uid, path

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
            Data retrieved from _store.

        Raises
        ------
        KeyError
            If data key (/flightid/grpid/uid) does not exist
        """

        if uid in self._cache:
            self.log.info("Loading data {} from cache.".format(uid))
            return self._cache[uid]
        else:
            path = self.join_path(flightid, grpid, uid)
            self.log.debug("Loading data %s from hdf5 _store.", path)

            with HDFStore(str(self.hdf5path)) as hdf:
                data = hdf.get(path)

            # Cache the data
            self._cache[uid] = data
            return data

    # See https://www.pytables.org/usersguide/libref/file_class.html#tables.File.set_node_attr
    # For more details on setting/retrieving metadata from hdf5 file using pytables
    # Note that the _v_ and _f_ prefixes are meant for instance variables and public methods
    # within pytables - so the inspection warning can be safely ignored

    def get_node_attrs(self, path) -> list:
        with tables.open_file(str(self.hdf5path)) as hdf:
            try:
                return hdf.get_node(path)._v_attrs._v_attrnames
            except tables.exceptions.NoSuchNodeError:
                raise ValueError("Specified path %s does not exist.", path)

    def _get_node_attr(self, path, attrname):
        with tables.open_file(str(self.hdf5path)) as hdf:
            try:
                return hdf.get_node_attr(path, attrname)
            except AttributeError:
                return None

    def _set_node_attr(self, path, attrname, value):
        with tables.open_file(str(self.hdf5path), 'a') as hdf:
            try:
                hdf.set_node_attr(path, attrname, value)
            except tables.exceptions.NoSuchNodeError:
                self.log.error("Unable to set attribute on path: %s key does not exist.")
                raise KeyError("Node %s does not exist", path)
            else:
                return True
