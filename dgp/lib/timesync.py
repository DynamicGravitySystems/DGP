# coding=utf-8

import numpy as np
from pandas import DataFrame
import pandas as pd
from pandas.tseries.frequencies import to_offset
from pandas.tseries.offsets import DateOffset
from scipy.interpolate import interp1d
import warnings


def interpolate_1d_vector(vector: np.array, factor: int):
    """
    Interpolate i.e. up sample a give 1D vector by interpolation factor

    Parameters
    ----------
    vector: np.array
        1D Data Vector
    factor: int
        Interpolation factor

    Returns
    -------
    np.array:
        1D Array interpolated by 'factor'

    """
    x = np.arange(np.size(vector))
    y = vector
    f = interp1d(x, y)
    # f = np.interp(x, x, y)

    x_extended_by_factor = np.linspace(x[0], x[-1], np.size(x) * factor)
    y_interpolated = np.zeros(np.size(x_extended_by_factor))

    i = 0
    for x in x_extended_by_factor:
        y_interpolated[i] = f(x)
        i += 1

    return y_interpolated


def find_time_delay(s1, s2, datarate=1, resolution: bool=False):
    """
    Finds the time shift or delay between two signals
    If s1 is advanced to s2, then the delay is positive.

    Parameters
    ----------
    s1: array-like
    s2: array-like
    datarate: int, optional
        Input data sample rate in Hz. If objects with time-like indexes are
        given in the first two arguments, then this argument is ignored.
    resolution: bool
        If False use data without oversampling
        If True, calculates time delay with 10* oversampling

    Returns
    -------
    Scalar:
        Time shift between s1 and s2. If datarate is not specified, then the
        delay is given in fractional samples. Otherwise, delay is given in
        seconds. If both inputs have a time-like index, then the frequency
        is inferred from there.

    """

    if hasattr(s1, 'index') and not hasattr(s2, 'index'):
        warnings.warn('s2 has no index. Ignoring index for s1.', stacklevel=2)
        in1 = s1.values
        in2 = s2
    elif not hasattr(s1, 'index') and hasattr(s2, 'index'):
        warnings.warn('s1 has no index. Ignoring index for s1.', stacklevel=2)
        in1 = s1
        in2 = s2.values
    elif hasattr(s1, 'index') and hasattr(s2, 'index'):
        if not isinstance(s1.index, pd.DatetimeIndex):
            warnings.warn('Index of s1 is not a DateTimeIndex. Ignoring both '
                          'indexes.', stacklevel=2)
            in1 = s1.values

            try:
                in2 = s2.values
            except AttributeError:
                in2 = s2

        elif not isinstance(s2.index, pd.DatetimeIndex):
            warnings.warn('Index of s2 is not a DateTimeIndex. Ignoring both '
                          'indexes.', stacklevel=2)
            in2 = s2.values

            try:
                in1 = s1.values
            except AttributeError:
                in1 = s1
        else:
            in1 = s1.values
            in2 = s2.values

            # TODO: Option to normalize the two indexes
            if s1.index.freq is not None:
                s1_freq = s1.index.freq
            else:
                s1_freq = s1.index.inferred_freq

            if s2.index.freq is not None:
                s2_freq = s2.index.freq
            else:
                s2_freq = s2.index.inferred_freq

            if s1_freq != s2_freq:
                raise ValueError('Indexes have different frequencies')

            if s1_freq is None:
                raise ValueError('Index frequency cannot be inferred')

            freq = pd.to_timedelta(to_offset(s1_freq)).microseconds * 1e-6
            datarate = 1 / freq

    else:
        in1 = s1
        in2 = s2

    lagwith = 200
    len_s1 = len(in1)

    if not resolution:
        c = np.correlate(in1, in2, mode='full')
        scale = datarate
    else:
        in1 = interpolate_1d_vector(in1, datarate)
        in2 = interpolate_1d_vector(in2, datarate)
        c = np.correlate(in1, in2, mode='full')
        scale = datarate * 10

    shift = np.linspace(-lagwith, lagwith, 2 * lagwith + 1)
    corre = c[len_s1 - 1 - lagwith:len_s1 + lagwith]
    maxi = np.argmax(corre)
    dm1 = abs(corre[maxi] - corre[maxi - 1])
    dp1 = abs(corre[maxi] - corre[maxi + 1])
    if dm1 < dp1:
        x = shift[maxi-2: maxi+1]
        z = np.polyfit(x, corre[maxi - 2:maxi + 1], 2)
    else:
        z = np.polyfit(shift[maxi - 1:maxi + 2], corre[maxi - 1:maxi + 2], 2)

    dt1 = z[1] / (2 * z[0])
    delay = dt1 / scale
    return dt1 / scale


def shift_frame(frame, delay):
    return frame.tshift(delay * 1e6, freq='U')


def shift_frames(gravity: DataFrame, gps: DataFrame, eotvos: DataFrame,
                 datarate=10) -> DataFrame:
    """
    Synchronize and join a gravity and gps DataFrame (DF) into a single time
    shifted DF.
    Time lag/shift is found using the find_time_delay function, which cross
    correlates the gravity channel with Eotvos corrections.
    The DFs (gravity and gps) are then upsampled to a 1ms period using cubic
    interpolation.
    The Gravity DataFrame is then shifted by the time shift factor returned by
    find_time_delay at ms precision.
    We then join the GPS DF on the Gravity DF using a left join resulting in a
    single DF with Gravity and GPS data at 1ms frequency.
    Finally the joined DF is downsampled back to the original frequency 1/10Hz

    Parameters
    ----------
    gravity: DataFrame
        Gravity data DataFrame to time shift and join
    gps: DataFrame
        GPS/Trajectory DataFrame to correlate with Gravity data
    eotvos: DataFrame
        Eotvos correction for input Trajectory
    datarate: int
        Scalar datarate in Hz

    Returns
    -------
    DataFrame:
        Synchronized and joined DataFrame containing:
            set{gravity.columns, gps.columns}
        If gps contains duplicate column names relative to gravity DF, they will
        be suffixed with '_gps'

    """

    # eotvos = calc_eotvos(gps['lat'].values, gps['longitude'].values,
    #                      gps['ell_ht'].values, datarate)
    delay = find_time_delay(gravity['gravity'].values, eotvos, 10)
    time_shift = DateOffset(seconds=delay)

    # Upsample and then shift:
    grav_1ms = gravity.resample('1L').interpolate(method='cubic').fillna(method='pad')
    gps_1ms = gps.resample('1L').interpolate(method='cubic').fillna(method='pad')
    gravity_synced = grav_1ms.shift(freq=time_shift)  # type: DataFrame

    # Join shifted DataFrames:
    joined = gravity_synced.join(gps_1ms, how='left', rsuffix='_gps')

    # Now downsample back to original period
    down_sample = "{}S".format(1/datarate)
    # TODO: What method to use when downsampling - mean, or some other method?
    # Can use .apply() to apply custom filter/sampling method
    return joined.resample(down_sample).mean()

