from datetime import datetime, timedelta
import pandas as pd
import collections
from functools import lru_cache

leap_second_table = [(datetime(1980, 1, 1), datetime(1981, 7, 1)),
                     (datetime(1981, 7, 1), datetime(1982, 7, 1)),
                     (datetime(1982, 7, 1), datetime(1983, 7, 1)),
                     (datetime(1983, 7, 1), datetime(1985, 7, 1)),
                     (datetime(1985, 7, 1), datetime(1988, 1, 1)),
                     (datetime(1988, 1, 1), datetime(1990, 1, 1)),
                     (datetime(1990, 1, 1), datetime(1991, 1, 1)),
                     (datetime(1991, 1, 1), datetime(1992, 7, 1)),
                     (datetime(1992, 7, 1), datetime(1993, 7, 1)),
                     (datetime(1993, 7, 1), datetime(1994, 7, 1)),
                     (datetime(1994, 7, 1), datetime(1996, 1, 1)),
                     (datetime(1996, 1, 1), datetime(1997, 7, 1)),
                     (datetime(1997, 7, 1), datetime(1999, 1, 1)),
                     (datetime(1999, 1, 1), datetime(2006, 1, 1)),
                     (datetime(2006, 1, 1), datetime(2009, 1, 1)),
                     (datetime(2009, 1, 1), datetime(2012, 7, 1)),
                     (datetime(2012, 7, 1), datetime(2015, 7, 1)),
                     (datetime(2015, 7, 1), datetime(2017, 1, 1))]


def datetime_to_sow(dt):
    def _to_sow(dt):
        delta = dt - datetime(1980, 1, 6)
        week = delta.days // 7
        sow = (delta.days % 7) * 86400. + delta.seconds + delta.microseconds * 1e-6
        return week, sow

    if isinstance(dt, collections.Iterable):
        res = []
        for i in dt:
            res.append(_to_sow(i))
        return res
    else:
        return _to_sow(dt)


def convert_gps_time(gpsweek, gpsweekseconds, format='unix'):
    """
    Converts a GPS time format (weeks + seconds since 6 Jan 1980) to a UNIX
    timestamp (seconds since 1 Jan 1970) without correcting for UTC leap
    seconds.

    Static values gps_delta and gpsweek_cf are defined by the below functions
    (optimization) gps_delta is the time difference (in seconds) between UNIX
    time and GPS time.

    gps_delta = (dt.datetime(1980, 1, 6) - dt.datetime(1970, 1, 1)).total_seconds()

    gpsweek_cf is the coefficient to convert weeks to seconds
    gpsweek_cf = 7 * 24 * 60 * 60  # 604800

    Parameters
    ----------
    gpsweek : int
        Number of weeks since beginning of GPS time (1980-01-06 00:00:00)

    gpsweekseconds : float
        Number of seconds since the GPS week parameter

    format : {'unix', 'datetime'}
        Format of returned value

    Returns
    -------
    float or :obj:`datetime`
        UNIX timestamp (number of seconds since 1970-01-01 00:00:00) without
        leapseconds subtracted if 'unix' is specified for format.
        Otherwise, a :obj:`datetime` is returned.
    """
    # GPS time begins 1980 Jan 6 00:00, UNIX time begins 1970 Jan 1 00:00
    gps_delta = 315964800.0
    gpsweek_cf = 604800

    if isinstance(gpsweek, pd.Series) and isinstance(gpsweekseconds, pd.Series):
        gps_ticks = (gpsweek.astype('float64') * gpsweek_cf) + gpsweekseconds.astype('float64')
    else:
        gps_ticks = (float(gpsweek) * gpsweek_cf) + float(gpsweekseconds)

    timestamp = gps_delta + gps_ticks

    if format == 'unix':
        return timestamp

    elif format == 'datetime':
        return datetime(1970, 1, 1) + pd.to_timedelta(timestamp * 1e9)

def leap_seconds(**kwargs):
    """
    Look-up for the number of leap seconds for a given date

    Parameters
    ----------
    week : int, optional
        Number of weeks since beginning of GPS time (1980-01-06 00:00:00)

    seconds : float, optional
        If week is specified, then seconds of week since the beginning of
        Sunday of that week, otherwise, Unix time in seconds since
        January 1, 1970 UTC.

    date : :obj:`str`, optional
        Date string in the format specified by dateformat.

    dateformat : :obj:`str`, optional
        Format of the date string if date is used. Default: '%m-%d-%Y'

        .. _Format codes:
            https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior

    datetime : :obj:`datetime`

    Returns
    -------
    int
        Number of accumulated leap seconds as of the given date.
    """
    if 'seconds' in kwargs:
        if 'week' in kwargs:
            dt = (datetime(1980, 1, 6) +
                  timedelta(weeks=kwargs['week']) +
                  timedelta(seconds=kwargs['seconds']))
        else:
            # TODO Check for value out of bounds?
            dt = (datetime(1970, 1, 1) +
                  timedelta(seconds=kwargs['seconds']))

    elif 'date' in kwargs:
        if 'dateformat' in kwargs:
            fmt = kwargs['dateformat']
        else:
            fmt = '%m-%d-%Y'

        dt = datetime.strptime(kwargs['date'], fmt)

    elif 'datetime' in kwargs:
        dt = kwargs['datetime']

    else:
        raise ValueError('Only valid keyword inputs are GPS time in week '
                         'number and seconds of week, Unix time in seconds '
                         'since January 1, 1970 UTC, or datetime.')

    return _get_leap_seconds(dt)


@lru_cache(maxsize=1000)
def _get_leap_seconds(dt):
    ls = 0
    for entry in leap_second_table:
        if entry[0] <= dt < entry[1]:
            break
        else:
            ls += 1
    return ls


def datenum_to_datetime(timestamp):
    raise NotImplementedError
    # if isinstance(timestamp, pd.Series):
    #     return (timestamp.astype(int).map(datetime.fromordinal) +
    #             pd.to_timedelta(timestamp % 1, unit='D') -
    #             pd.to_timedelta('366 days'))
    # else:
    #     return (datetime.fromordinal(int(timestamp) - 366) +
    #             timedelta(days=timestamp % 1))
