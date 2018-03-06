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
import fnmatch
import os
import re

from .time_utils import convert_gps_time
from .etc import interp_nans


def _extract_bits(bitfield, columns=None, as_bool=False):
    """
    Function that extracts bitfield values from integers.

    A pandas.Series or numpy.array of integers is converted to a
    pandas.DataFrame of 1/0 or True/False values for as many bits
    there are in the integer - least signficant bit first - or for as many
    column names that are given.

    Parameters
    ----------
    bitfield : numpy.array or pandas.Series
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


DGS_AT1A_INTERP_FIELDS = {'gravity', 'long_accel', 'cross_accel', 'beam',
                          'temp', 'pressure', 'Etemp'}


def read_at1a(path, columns=None, fill_with_nans=True, interp=False,
              skiprows=None):
    """
    Read and parse gravity data file from DGS AT1A (Airborne) meter.

    CSV Columns:
        gravity, long, cross, beam, temp, status, pressure, Etemp, GPSweek,
        GPSweekseconds

    Parameters
    ----------
    path : str
        Filesystem path to gravity data file
    columns: List
        Optional List of fields to specify when importing the data, otherwise
        defaults are assumed.
        This can be used if the data file has fields in an abnormal order
    fill_with_nans : boolean, default True
        Fills time gaps with NaNs for all fields
    interp : boolean, default False
        Interpolate all NaNs for fields of type numpy.number
    skiprows

    Returns
    -------
    pandas.DataFrame
        Gravity data indexed by datetime.
    """
    columns = columns or ['gravity', 'long_accel', 'cross_accel', 'beam',
                          'temp', 'status', 'pressure', 'Etemp', 'GPSweek',
                          'GPSweekseconds']

    df = pd.read_csv(path, header=None, engine='c', na_filter=False,
                     skiprows=skiprows)
    df.columns = columns

    # expand status field
    status_field_names = ['clamp', 'unclamp', 'gps_sync', 'feedback',
                          'reserved1', 'reserved2', 'ad_lock', 'cmd_rcvd',
                          'nav_mode_1', 'nav_mode_2', 'plat_comm', 'sens_comm',
                          'gps_input', 'ad_sat', 'long_sat', 'cross_sat',
                          'on_line']

    status = _extract_bits(df['status'], columns=status_field_names,
                           as_bool=True)

    df = pd.concat([df, status], axis=1)
    df.drop('status', axis=1, inplace=True)

    # create datetime index
    dt_list = []
    for (week, sow) in zip(df['GPSweek'], df['GPSweekseconds']):
        dt_list.append(convert_gps_time(week, sow, format='datetime'))

    df.index = pd.DatetimeIndex(dt_list)

    if fill_with_nans:
        # select rows where time is synced with the GPS NMEA
        df = df.loc[df['gps_sync']]

        # fill gaps with NaNs
        interval = '100000U'
        index = pd.date_range(df.index[0], df.index[-1], freq=interval)
        df = df.reindex(index)

    # TODO: Replace interp_nans with pandas interpolate
    if interp:
        numeric = df.select_dtypes(include=[np.number])
        numeric = numeric.interpolate(method='time')

        # replace columns
        for col in numeric.columns:
            df[col] = numeric[col]

    return df


def _parse_ZLS_file_name(filename):
    # split by underscore
    fname = [e.split('.') for e in filename.split('_')]

    # split hour from day and then flatten into one tuple
    b = [int(el) for fname_parts in fname for el in fname_parts]

    # generate datetime
    c = datetime.datetime(b[0], 1, 1) + datetime.timedelta(days=b[2] - 1,
                                                           hours=b[1])
    return c


def _read_ZLS_format_file(filepath):
    col_names = ['line_name', 'year', 'day', 'hour', 'minute', 'second',
                 'sensor', 'spring_tension', 'cross_coupling',
                 'raw_beam', 'vcc', 'al', 'ax', 've2', 'ax2', 'xacc2',
                 'lacc2', 'xacc', 'lacc', 'par_port', 'platform_period']

    col_widths = [10, 4, 3, 2, 2, 2, 8, 8, 7, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
                  8, 6]

    time_columns = ['year', 'day', 'hour', 'minute', 'second']

    # read into dataframe
    df = pd.read_fwf(filepath, widths=col_widths, names=col_names)

    day_fmt = lambda x: '{:03d}'.format(x)
    time_fmt = lambda x: '{:02d}'.format(x)

    t = df['year'].map(str) + df['day'].map(day_fmt) + \
        df['hour'].map(time_fmt) + df['minute'].map(time_fmt) + \
        df['second'].map(time_fmt)

    # index by datetime
    df.index = pd.to_datetime(t, format='%Y%j%H%M%S')
    df.drop(time_columns, axis=1, inplace=True)

    return df


def read_zls(dirpath, begin_time=None, end_time=None, excludes=['.*']):
    """
    Read and parse gravity data file from ZLS meter.

    Files are segmented by hour and data is presented as ASCII in a fixed-width
    format.

    Columns:
        line name, year, day, hour, minute, second, gravity, spring tension, \
        cross coupling, raw beam, vcc, al, ax, ve2, ax2, xacc2, lacc2, xacc, \
        lacc, par port, platform period

    Parameters
    ----------
    dirpath : str
        Filesystem path to directory containing files
    begin_time : datetime, optional
        Data start time if not importing from the first file in the directory
    end_time : datetime, optional
        Data end time if not importing to the last file in the directory
    excludes : list
        Files and directories to exclude from directory listing.

    Returns
    -------
    pandas.DataFrame
        Gravity data indexed by datetime.
    """

    excludes = r'|'.join([fnmatch.translate(x) for x in excludes]) or r'$.'

    # list files in directory
    files = [_parse_ZLS_file_name(f) for f in os.listdir(dirpath)
             if os.path.isfile(os.path.join(dirpath, f))
             if not re.match(excludes, f)]

    # sort files
    files = sorted(files)

    # validate begin and end times
    if begin_time is None and end_time is None:
        begin_time = files[0]
        end_time = files[-1] + datetime.timedelta(hours=1)

    elif begin_time is None and end_time is not None:
        begin_time = files[0]
        if end_time < begin_time or end_time > files[-1]:
            raise ValueError('end time ({end}) is out of bounds'
                             .format(end=end_time))

    elif begin_time is not None and end_time is None:
        end_time = files[-1]
        if begin_time > end_time or begin_time < files[0]:
            raise ValueError('begin time ({begin}) is out of bounds'
                             .format(begin=begin_time))

    else:
        if begin_time > end_time:
            raise ValueError('begin time ({begin}) is after end time ({end})'
                             .format(begin=begin_time, end=end_time))

    # filter file list based on begin and end times
    files = filter(lambda x: (x >= begin_time and x <= end_time)
                             or (begin_time >= x and
                                 begin_time <= x + datetime.timedelta(hours=1))
                             or (end_time - datetime.timedelta(hours=1) <= x and
                                 end_time >= x), files)

    # convert to ZLS-type file names
    files = [dt.strftime('%Y_%H.%j') for dt in files]

    df = pd.DataFrame()
    for f in files:
        frame = _read_ZLS_format_file(os.path.join(dirpath, f))
        df = pd.concat([df, frame])

    df.drop(df.index[df.index < begin_time], inplace=True)
    df.drop(df.index[df.index > end_time], inplace=True)

    return df


FUNCTION_MAP = {'at1a': read_at1a, 'zls': read_zls}
