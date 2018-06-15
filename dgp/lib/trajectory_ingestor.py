# coding=utf-8

"""
trajectory_ingestor.py
Library for trajectory data import functions

"""
import numpy as np
import pandas as pd

from .time_utils import leap_seconds, convert_gps_time, datenum_to_datetime
from .etc import interp_nans


TRAJECTORY_INTERP_FIELDS = {'lat', 'long', 'ell_ht'}


def import_trajectory(filepath, delim_whitespace=False, interval=0,
                      interp=False, is_utc=False, columns=None, skiprows=None,
                      timeformat='sow'):
    """
    Read and parse ASCII trajectory data in a comma-delimited format.

    Parameters
    ----------
    filepath : str or File-like object.
        Filesystem path to trajectory data file
    delim_whitespace : bool
    interval : float, Optional
        Output data rate. Default behavior is to infer the rate.
    interp : Union[List[str], List[int]], Optional
        Gaps in data will be filled with interpolated values. List of
        column indices (list of ints) or list of column names (list of strs)
        to interpolate. Default behavior is not to interpolate.
    is_utc : bool, Optional
        Indicates that the timestamps are UTC. The index datetimes will be
        shifted to remove the GPS-UTC leap second offset.
    columns : List[str]
        Strings to use as the column names.
        If none supplied (default), columns will be determined based on
        timeformat
    skiprows : Union[None, Iterable, int, Callable], Optional
        Line numbers to skip (0-indexed) or number of lines to skip (int) at
        the start of the file. If callable, the callable function will be
        evaluated against the row indices, returning True if the row should
        be skipped and False otherwise. An example of a valid callable argument
        would be lambda x: x in [0, 2].
    timeformat : str
        'sow' | 'hms' | 'serial'  Default: 'hms'
        Indicates the time format to expect. The 'sow' format requires a field
        named 'week' with the GPS week, and a field named 'sow' with the GPS
        seconds of week. The 'hms' format requires a field named 'mdy' with the
        date in the format 'MM/DD/YYYY', and a field named 'hms' with the time
        in the format 'HH:MM:SS.SSS'. The 'serial' format (not yet implemented)
        requires a field named 'datenum' with the serial date number.

    Returns
    -------
    DataFrame
        Pandas DataFrame of ingested Trajectory data.

    """

    df = pd.read_csv(filepath, delim_whitespace=delim_whitespace, header=None,
                     engine='c', na_filter=False, skiprows=skiprows)

    # assumed position of these required fields
    if columns is None:
        if timeformat.lower() == 'sow':
            columns = ['week', 'sow', 'lat', 'long', 'ell_ht']
        elif timeformat.lower() == 'hms':
            columns = ['mdy', 'hms', 'lat', 'long', 'ell_ht']
        elif timeformat.lower() == 'serial':
            columns = ['datenum', 'lat', 'long', 'ell_ht']
        else:
            raise ValueError('timeformat value {fmt!r} not recognized'
                             .format(fmt=timeformat))

    # 'None' indicates a not-needed field
    # if a field is after all non-essentials, and is not named, it will be removed
    if len(df.columns) > len(columns):
            columns.extend([None] * (len(df.columns) - len(columns)))

    # drop unwanted columns
    drop_list = list()
    for idx, val in enumerate(columns):
        if val is None:
            drop_list.append(idx)

    columns = [x for x in columns if x is not None]

    if drop_list:
        df.drop(df.columns[drop_list], axis=1, inplace=True)

    df.columns = columns

    # create index
    if timeformat == 'sow':
        df.index = convert_gps_time(df['week'], df['sow'], format='datetime')
        df.drop(['sow', 'week'], axis=1, inplace=True)
    elif timeformat == 'hms':
        df.index = pd.to_datetime(df['mdy'].str.strip() + df['hms'].str.strip(),
                                  format="%m/%d/%Y%H:%M:%S.%f")
        df.drop(['mdy', 'hms'], axis=1, inplace=True)
    elif timeformat == 'serial':
        raise NotImplementedError
        #df.index = datenum_to_datetime(df['datenum'])

    # remove leap second
    if is_utc:
        # TO DO: Check dates at beginning and end to determine whether a leap second was added in the middle of the survey.
        shift = leap_seconds(df.index[0])
        df.index = df.index.shift(-shift, freq='S')

    # set or infer the interval
    # TO DO: Need to infer interval for both cases to know whether resample
    if interval > 0:
        offset_str = '{:d}U'.format(int(interval * 1e6))
    else:
        offset_str = '100000U'

    # fill gaps with NaNs
    new_index = pd.date_range(df.index[0], df.index[-1], freq=offset_str)
    df = df.reindex(new_index)

    if interp:
        numeric = df.select_dtypes(include=[np.number])
        numeric = numeric.interpolate(method='time')

        # replace columns
        for col in numeric.columns:
            df[col] = numeric[col]

    return df
