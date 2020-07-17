# -*- coding: utf-8 -*-
import logging
import warnings
from pathlib import Path
from typing import Any

import tables
import pandas.io.pytables
from pandas import HDFStore, DataFrame

from dgp.core.models.datafile import DataFile

__all__ = ['HDF5Manager']
# Suppress PyTables warnings due to mixed data-types (typically NaN's in cols)
warnings.filterwarnings('ignore',
                        category=pandas.io.pytables.PerformanceWarning)

# Define Data Types/Extensions
HDF5_NAME = 'dgpdata.hdf5'


class HDF5Manager:
    """HDF5Manager is a utility class used to read/write pandas DataFrames to and from
    an HDF5 data file. This class is essentially a wrapper around the pandas HDFStore,
    and features of the underlying pytables module, designed to allow easy storage
    and retrieval of DataFrames based on a :obj:`~dgp.core.models.data.DataFile`

    HDF5Manager should not be directly instantiated, it provides classmethod's
    and staticmethod's to store/retrieve data, without maintaining state,
    except for the data cache as described below.

    The HDF5 Manager maintains a class level cache, which obviates the need to perform
    expensive file-system operations to load data that has previously been loaded during
    a session.

    HDF5Manager also provides utility methods to allow read/write of metadata attributes
    on a particular node within the HDF5 file.

    """
    log = logging.getLogger(__name__)
    _cache = {}

    @classmethod
    def save_data(cls, data: DataFrame, datafile: DataFile, path: Path) -> bool:
        """
        Save a Pandas Series or DataFrame to the HDF5 Store

        Data is added to the local cache, keyed by its generated UID.
        The generated UID is passed back to the caller for later reference.

        Parameters
        ----------
        data : DataFrame
            Data object to be stored on disk via specified format.
        datafile : DataFile
            The DataFile metadata associated with the supplied data
        path : Path
            Path to the HDF5 file

        Returns
        -------
        bool:
            True on successful save

        Raises
        ------
        :exc:`FileNotFoundError`
        :exc:`PermissionError`

        """

        cls._cache[datafile] = data

        with HDFStore(str(path)) as hdf:
            try:
                hdf.put(datafile.nodepath, data, format='fixed', data_columns=True)
            except (IOError, PermissionError):  # pragma: no cover
                cls.log.exception("Exception writing file to HDF5 _store.")
                raise
            else:
                cls.log.info(f"Wrote file to HDF5 _store at node: {datafile.nodepath}")

        return True

    @classmethod
    def load_data(cls, datafile: DataFile, path: Path) -> DataFrame:
        """
        Load data from a managed repository by UID
        This public method is a dispatch mechanism that calls the relevant
        loader based on the data type of the data represented by UID.
        This method will first check the local cache for UID, and if the key
        is not located, will load it from the HDF5 Data File.

        Parameters
        ----------
        datafile : DataFile
        path : Path
            Path to the HDF5 file where datafile is stored

        Returns
        -------
        DataFrame
            Data retrieved from _store.

        Raises
        ------
        KeyError
            If data key (/flightid/grpid/uid) does not exist
        """
        if datafile in cls._cache:
            cls.log.info(f"Loading data node {datafile.uid!s} from cache.")
            return cls._cache[datafile]
        else:
            cls.log.debug(f"Loading data node {datafile.nodepath} from hdf5store.")

            try:
                with HDFStore(str(path), mode='r') as hdf:
                    data = hdf.get(datafile.nodepath)
            except OSError as e:
                cls.log.exception(e)
                raise FileNotFoundError from e
            except KeyError as e:
                cls.log.exception(e)
                raise

            # Cache the data
            cls._cache[datafile] = data
            return data

    @classmethod
    def delete_data(cls, file: DataFile, path: Path) -> bool:
        raise NotImplementedError

    # See https://www.pytables.org/usersguide/libref/file_class.html#tables.File.set_node_attr
    # For more details on setting/retrieving metadata from hdf5 file using pytables
    # Note that the _v_ and _f_ prefixes are meant for instance variables and public methods
    # within pytables - so the inspection warning can be safely ignored

    @classmethod
    def list_node_attrs(cls, nodepath: str, path: Path) -> list:
        with tables.open_file(str(path), mode='r') as hdf:
            try:
                return hdf.get_node(nodepath)._v_attrs._v_attrnames
            except tables.exceptions.NoSuchNodeError:
                raise KeyError(f"Specified node {nodepath} does not exist.")

    @classmethod
    def _get_node_attr(cls, nodepath, attrname, path: Path):
        with tables.open_file(str(path), mode='r') as hdf:
            try:
                return hdf.get_node_attr(nodepath, attrname)
            except AttributeError:
                return None

    @classmethod
    def _set_node_attr(cls, nodepath: str, attrname: str, value: Any, path: Path):
        with tables.open_file(str(path), 'a') as hdf:
            try:
                hdf.set_node_attr(nodepath, attrname, value)
            except tables.exceptions.NoSuchNodeError:
                raise KeyError(f"Specified node {nodepath} does not exist")
            else:
                return True

    @classmethod
    def clear_cache(cls):
        del cls._cache
        cls._cache = {}
