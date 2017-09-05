# coding=utf-8

"""
gravity_ingestor.py
Library for gravity data import functions

"""

import csv
import numpy as np
import pandas as pd
import functools
import datetime
import struct

from .time_utils import convert_gps_time


def safe_float(data, none_val=np.nan):
    if data is None:
        return none_val
    try:
        return float(data)
    except ValueError:
        return none_val

def _extract_bits(bitfield, columns=None, as_bool=False):
    """
    Function that extracts bitfield values from integers.

    A pandas.Series or numpy.array of integers is converted to a
    pandas.DataFrame of 1/0 or True/False values for as many bits
    there are in the integer - least signficant bit first - or for as many
    column names that are given.

    Parameters
    ----------
    bitfields : numpy.array or pandas.Series
        16, 32, or 64-bit integers
    columns : list, optional
        If a list is given, then the column names are given to the resulting
        columns in the order listed.
    as_bool : bool, optional
        If True, then values in returned DataFrame are type numpy.bool_

    Returns
    -------
    pandas.DataFrame

    """
    def _unpack_bits(n):
        x = np.array(struct.unpack('4B', struct.pack('>I', n)), dtype=np.uint8)
        return np.flip(np.unpackbits(x), axis=0)

    data = bitfield.apply(_unpack_bits)
    df = pd.DataFrame(np.column_stack(list(zip(*data))))

    # set column names
    if columns is not None:
        # remove fields from the end if not named
        if len(columns) < len(df.columns):
            df.drop(df.columns[range(len(columns), len(df.columns))], axis=1, inplace=True)
            df.columns = columns
        elif len(columns) > len(df.columns):
            df.columns = columns[:len(df.columns)]
        else:
            df.columns = columns

    if as_bool:
        return df.astype(np.bool_)
    else:
        return df

def read_at1a(path, fill_with_nans=True):
    """
    Read and parse gravity data file from DGS AT1A (Airborne) meter.

    CSV Columns:
        gravity, long, cross, beam, temp, status, pressure, Etemp, GPSweek, GPSweekseconds

    Parameters
    ----------
    path : str
        Filesystem path to gravity data file

    Returns
    -------
    pandas.DataFrame
        Gravity data indexed by datetime.
    """
    fields = ['gravity', 'long', 'cross', 'beam', 'temp', 'status', 'pressure', 'Etemp', 'GPSweek', 'GPSweekseconds']

    data = []
    df = pd.read_csv(path, header=None, engine='c', na_filter=False)
    df.columns = fields

    # expand status field
    status_field_names = ['clamp', 'unclamp', 'gps_sync', 'feedback', 'r1',
                          'r2', 'ad_lock', 'rcvd', 'mode_1', 'mode_2',
                          'plat_com', 'sens_com', 'gps_time', 'ad_sat',
                          'long_accel', 'cross_accel', 'on_line']

    status = _extract_bits(df['status'], columns=status_field_names,
                          as_bool=True)

    # df = df.append(status)
    df = pd.concat([df, status], axis=1)
    df.drop('status', axis=1, inplace=True)

    # create datetime index
    dt_list = []
    for (week, sow) in zip(df['GPSweek'], df['GPSweekseconds']):
        dt_list.append(convert_gps_time(week, sow, format='datetime'))

    df.index = pd.DatetimeIndex(dt_list)

    if fill_with_nans:
        # select rows where time is synced with the GPS NMEA
        df = df.loc[df['gps_time']]

        # fill gaps with NaNs
        interval = '100000U'
        index = pd.date_range(df.index[0], df.index[-1], freq=interval)
        df = df.reindex(index)

    return df
