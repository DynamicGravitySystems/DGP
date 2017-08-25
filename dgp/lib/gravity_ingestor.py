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

from .time_utils import convert_gps_time

def safe_float(data, none_val=np.nan):
    if data is None:
        return none_val
    try:
        return float(data)
    except ValueError:
        return none_val

def read_at1m(path):
    """
    read_at1m :: String -> DataFrame

    Read and parse gravity data file from DGS AT1M meter.
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
