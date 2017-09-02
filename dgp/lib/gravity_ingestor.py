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
    def _unpack_bits(n):
        # assumes 32-bit number
        x = np.array(struct.unpack('4B', struct.pack('>I', n)), dtype=np.uint8)
        return np.flip(np.unpackbits(x), axis=0)

    data = bitfield.apply(_unpack_bits)
    df = pd.DataFrame(np.column_stack(list(zip(*data))))

    # TO DO: simplify?
    if columns is not None:
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

def read_at1a(path):
    """
    read_at1a :: String -> DataFrame

    Read and parse gravity data file from DGS AT1A (Airborne) meter.
    CSV Columns:
        gravity, long, cross, beam, temp, status, pressure, Etemp, GPSweek, GPSweekseconds
    :param path: Filesystem path to gravity data file
    :return: Pandas DataFrame of gravity data indexed by datetime, with UNIX timestamp converted from GPS time
    """
    fields = ['gravity', 'long', 'cross', 'beam', 'temp', 'status', 'pressure', 'Etemp', 'GPSweek', 'GPSweekseconds']

    data = []
    df = pd.read_csv(path, header=None, engine='c', na_filter=False)
    df.columns = fields

    # create datetime index
    dt_list = []
    for (week, sow) in zip(df['GPSweek'], df['GPSweekseconds']):
        dt_list.append(convert_gps_time(week, sow, format='datetime'))

    df.index = pd.DatetimeIndex(dt_list)

    # resample
    # offset_str = '{:d}U'.format(int(0.1 * 1e6))
    offset_str = '100000U'
    df = df.resample(offset_str).mean()

    return df
