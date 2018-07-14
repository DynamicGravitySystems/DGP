Data Management in DGP
======================

DGP manages and interacts with a variety of forms of Data.
Imported raw data (GPS or Gravity) is ingested and maintained internally as a
:class:`pandas.DataFrame` or :class:`pandas.Series` from their raw
representation in comma separated value (CSV) files.
The ingestion process performs type-casts, filling/interpolation of missing
values, and time index creation/conversion functions to result in a
ready-to-process DataFrame.

These DataFrames are then stored in the project's HDF5_ data-file, which
natively supports (with PyTables_ and Pandas) the storage and retrieval of
DataFrames and Series.

.. _HDF5: https://portal.hdfgroup.org/display/support
.. _PyTables: https://www.pytables.org/

To facilitate storage and retrieval of data within the project, the
:class:`~dgp.core.hdf5_manager.HDF5Manager` class provides an easy to use
wrapper around the :class:`pandas.HDFStore` and provides utility methods
for getting/setting meta-data attributes on nodes.

.. py:module:: dgp.core.hdf5_manager

.. autoclass:: HDF5Manager
    :undoc-members:
    :private-members:
