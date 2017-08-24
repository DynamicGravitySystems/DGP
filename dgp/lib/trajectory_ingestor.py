# coding=utf-8

"""
trajectory_ingestor.py
Library for trajectory data import functions

"""

import csv
import numpy as np
import pandas as pd
import functools
import datetime

from .time_utils import leap_seconds

def _interp_nans(y):
    nans = np.isnan(y)
    x = lambda z: z.nonzero()[0]
    y[nans] = np.interp(x(nans), x(~nans), y[~nans])

def import_trajectory(filepath, delim_whitespace=False, interval=0, interp=None, is_utc=False,
                      columns=None, skiprows=None):
    """
    import_trajectory

    Read and parse ASCII trajectory data in a comma-delimited format.

    :param path: str
        Filesystem path to trajectory data file
    :param interval: float, default 0
        Output data rate. Default behavior is to infer the rate.
    :param interp: list of ints or list of strs, default None
        Gaps in data will be filled with interpolated values. List of
        column indices (list of ints) or list of column names (list of strs)
        to interpolate. Default behavior is not to interpolate.
    :param is_utc: boolean, default False
        Indicates that the timestamps are UTC. The index datetimes will be
        shifted to remove the GPS-UTC leap second offset.
    :param colums: list of strs, default None
        Strings to use as the column names.
    :param skiprows: list-like or integer or callable, default None
        Line numbers to skip (0-indexed) or number of lines to skip (int) at
        the start of the file. If callable, the callable function will be
        evaluated against the row indices, returning True if the row should
        be skipped and False otherwise. An example of a valid callable argument
        would be lambda x: x in [0, 2].
    :return: DataFrame
    """

    df = pd.read_csv(filepath, delim_whitespace=delim_whitespace, header=None, engine='c', na_filter=False, skiprows=skiprows)

    if columns is not None:
    	# relabel columns
    	df.columns = columns

    # create index
    df.index = pd.to_datetime(df['mdy'].str.strip() + ' ' + df['hms'].str.strip(), format="%m/%d/%Y %H:%M:%S.%f")

    # remove leap second
    if is_utc:
        # TO DO: Check dates at beginning and end to determine whether a leap second was added in the middle of the survey.
        # TO DO: First record may not be synced. Choose another, or several.
        shift = leap_seconds(df.index[0])
        df.index = df.index.shift(-shift, freq='S')

    # resample
    if interval > 0:
        offset_str = '{:d}U'.format(int(interval * 1e6))
    else:
        # TO DO: Infer interval
        offset_str = '100000U'

    df = df.resample(offset_str).mean()

    if interp is not None:
        # TO DO: Add a way for user to specify which columns to interpolate.
        df = df.apply(_interp_nans)

    return df
