import datetime
import pandas as pd

def convert_gps_time(gpsweek, gpsweekseconds, format='unix'):
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

    timestamp = gps_delta + gps_ticks

    if format == 'unix':
        return timestamp
    elif format == 'datetime':
        return datetime.datetime(1970, 1, 1) + pd.to_timedelta(timestamp, unit='s')

def leap_seconds(**kwargs):
    """
    leapseconds :: Variable type -> Integer

    Look-up for the number of leapseconds for a given date.

    :param week: Number of weeks since beginning of GPS time (1980-01-06 00:00:00)
    :param seconds: If week is specified, then seconds of week since the
                    beginning of Sunday of that week, otherwise, Unix time in
                    seconds since January 1, 1970 UTC.
    :param date: Date either in the format MM-DD-YYYY or MM/DD/YYYY
    :param datetime: datetime-like
    :return: (integer) Number of accumulated leap seconds as of the given date.
    """

    if 'seconds' in kwargs:
        # GPS week + seconds of week
        if 'week' in kwargs:
            dt = (datetime.datetime(1980, 1, 6) +
                  datetime.timedelta(weeks=kwargs['week']) +
                  datetime.timedelta(seconds=kwargs['seconds']))
        else:
        # TO DO: Check for value out of bounds?
        # week not specified, assume Unix time in seconds
            dt = (datetime.datetime(1970, 1, 1) +
                  datetime.timedelta(seconds=kwargs['seconds']))

    elif 'date' in kwargs:
        d = kwargs['date'].split('-')
        if len(d) != 3:
            d = kwargs['date'].split('/')
            if len(d) != 3:
                raise ValueError('Date not correctly formatted. '
                                 'Expect MM-DD-YYYY or MM/DD/YYYY. Got: {date}'
                                 .format(date=kwargs['date']))

        dt = datetime.datetime(int(d[2]), int(d[0]), int(d[1]))

    elif 'datetime' in kwargs:
        dt = kwargs['datetime']

    else:
        raise ValueError('Only valid keyword inputs are GPS time in week '
                         'number and seconds of week, Unix time in seconds '
                         'since January 1, 1970 UTC, or datetime.')

    ls_table = [(1980,1,1,1981,7,1),\
                (1981,7,1,1982,7,1),\
                (1982,7,1,1983,7,1),\
                (1983,7,1,1985,7,1),\
                (1985,7,1,1988,1,1),\
                (1988,1,1,1990,1,1),\
                (1990,1,1,1991,1,1),\
                (1991,1,1,1992,7,1),\
                (1992,7,1,1993,7,1),\
                (1993,7,1,1994,7,1),\
                (1994,7,1,1996,1,1),\
                (1996,1,1,1997,7,1),\
                (1997,7,1,1999,1,1),\
                (1999,1,1,2006,1,1),\
                (2006,1,1,2009,1,1),\
                (2009,1,1,2012,7,1),\
                (2012,7,1,2015,7,1),\
                (2015,7,1,2017,1,1)]

    leap_seconds = 0
    for entry in ls_table:
        if (dt >= datetime.datetime(entry[0], entry[1], entry[2]) and
            dt < datetime.datetime(entry[3],entry[4],entry[5])):
            break

        else:
            leap_seconds = leap_seconds + 1

    return leap_seconds
