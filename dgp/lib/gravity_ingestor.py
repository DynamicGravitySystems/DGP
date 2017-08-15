# coding=utf-8

"""
gravity_ingestor.py
Library for gravity data import functions

"""

import csv
import numpy as np
import pandas as pd


def safe_float(data, none_val=np.nan):
    if data is None:
        return none_val
    try:
        return float(data)
    except ValueError:
        return none_val


def convert_gps_time(gpsweek, gpsweekseconds):
    """
    convert_gps_time :: (String -> String) -> Float

    Converts a GPS time format (weeks + seconds since 6 Jan 1980) to a UNIX timestamp
    (seconds since 1 Jan 1970) without correcting for UTC leap seconds.

    Static values gps_delta and gpsweek_cf are defined by the below functions (optimization)
    gps_delta is the time difference (in seconds) between UNIX time and GPS time.
    gps_delta = (dt.datetime(1980, 1, 6) - dt.datetime(1970, 1, 1)).total_seconds()

    gpsweek_cf is the coefficient to convert weeks to seconds
    gpsweek_cf = 7 * 24 * 60 * 60  # 604800

    :param gpsweek: Number of weeks since beginning of GPS time (1980-01-06 00:00:00)
    :param gpsweekseconds: Number of seconds since the GPS week parameter
    :return: (float) unix timestamp (number of seconds since 1970-01-01 00:00:00)
    """
    # GPS time begins 1980 Jan 6 00:00, UNIX time begins 1970 Jan 1 00:00
    gps_delta = 315964800.0
    gpsweek_cf = 604800

    gps_ticks = (float(gpsweek) * gpsweek_cf) + float(gpsweekseconds)
    return gps_delta + gps_ticks


def read_at1m(path):
    """
    read_at1m :: String -> DataFrame

    Read and parse gravity data file from DGS AT1M meter.
    CSV Columns:
        gravity, long, cross, beam, temp, status, pressure, Etemp, GPSweek, GPSweekseconds
    :param path: Filesystem path to gravity data file
    :return: Pandas DataFrame of gravity data indexed by line number of file, with UNIX timestamp converted from GPS time
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

    return pd.DataFrame(data)
