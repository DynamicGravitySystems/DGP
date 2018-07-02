# -*- coding: utf-8 -*-
import logging
from pathlib import Path

import tables
from pandas import HDFStore, DataFrame

from ..models.data import DataFile

__all__ = ['HDFController']

# Define Data Types/Extensions
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
        logging.captureWarnings(True)
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

    def save_data(self, data: DataFrame, datafile: DataFile):
        """
        Save a Pandas Series or DataFrame to the HDF5 Store

        TODO: This doc is outdated
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
        datafile: DataFile

        Returns
        -------
        bool:
            True on sucessful save

        Raises
        ------

        """

        self._cache[datafile] = data

        with HDFStore(str(self.hdf5path)) as hdf:
            try:
                hdf.put(datafile.hdfpath, data, format='fixed', data_columns=True)
            except (IOError, FileNotFoundError, PermissionError):
                self.log.exception("Exception writing file to HDF5 _store.")
                raise
            else:
                self.log.info("Wrote file to HDF5 _store at node: %s", datafile.hdfpath)

        return True

    def load_data(self, datafile: DataFile) -> DataFrame:
        """
        Load data from a managed repository by UID
        This public method is a dispatch mechanism that calls the relevant
        loader based on the data type of the data represented by UID.
        This method will first check the local cache for UID, and if the key
        is not located, will load it from the HDF5 Data File.

        Parameters
        ----------

        Returns
        -------
        DataFrame
            Data retrieved from _store.

        Raises
        ------
        KeyError
            If data key (/flightid/grpid/uid) does not exist
        """

        if datafile in self._cache:
            self.log.info("Loading data {} from cache.".format(datafile.uid))
            return self._cache[datafile]
        else:
            self.log.debug("Loading data %s from hdf5 _store.", datafile.hdfpath)

            try:
                with HDFStore(str(self.hdf5path)) as hdf:
                    data = hdf.get(datafile.hdfpath)
            except Exception as e:
                self.log.exception(e)
                raise IOError("Could not load DataFrame from path: %s" % datafile.hdfpath)

            # Cache the data
            self._cache[datafile] = data
            return data

    def delete_data(self, file: DataFile) -> bool:
        raise NotImplementedError

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
