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
    data_fields = fields[:-2]

    data = []
    with open(path, newline='') as gravdata:
        reader = csv.DictReader(gravdata, fieldnames=fields)

        for row in reader:
            timestamp = convert_gps_time(row['GPSweek'], row['GPSweekseconds'])
            row_data = {k: safe_float(v) for k, v in row.items() if k in data_fields}
            row_data['timestamp'] = timestamp
            # row_time = {k: int(v) for k, v in row.items() if k in time_fields}
            data.append(row_data)

    df = pd.DataFrame(data)

    # create datetime index
    dt = datetime.datetime(1970, 1, 1) + pd.to_timedelta(df['timestamp'], unit='s')
    df.index = pd.DatetimeIndex(dt)

    # resample
    # offset_str = '{:d}U'.format(int(0.1 * 1e6))
    offset_str = '100000U'
    df = df.resample(offset_str).mean()

    return df
