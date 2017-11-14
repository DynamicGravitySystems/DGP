# coding=utf-8

# This file is part of DynamicGravityProcessor (https://github.com/DynamicGravitySystems/DGP).

import numpy as np
from pandas import DataFrame, Series
from pandas.tseries.offsets import DateOffset
from scipy.interpolate import interp1d

from dgp.lib.eotvos import calc_eotvos

# bradyzp: Updated function to remove dependency on scipy, using numpy.interp instead.
# bradyzp: Code cleanup and re-write docstrings to conform to project specs.


def interpolate_1d_vector(vector: np.array, factor: int):
    """
    Interpolate i.e. up sample a give 1D vector by specified interpolation factor

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
    # f = scipy.interpolate.interp1d(x, y)
    f = np.interp(x, x, y)

    x_extended_by_factor = np.linspace(x[0], x[-1], np.size(x) * factor)
    y_interpolated = np.zeros(np.size(x_extended_by_factor))

    i = 0
    for x in x_extended_by_factor:
        y_interpolated[i] = f(x)
        i += 1

    return y_interpolated


def find_time_delay(s1: np.array, s2: np.array, datarate: int, resolution: bool=False):
    """
    Python implementation of Daniel Aliod's time synchronization MATLAB function.
    Finds the time shift or delay between two arrays.
    If s1 is advanced to s2, timedelay is positive.

    Parameters
    ----------
    s1: np.array
        Input array 1
    s2: np.array
        Input array 2
    datarate: int
        Scalar data sampling rate in Hz
    resolution: bool
        If False use data without oversampling
        If True, calculates time delay with 10* oversampling

    Returns
    -------
    Scalar:
        Time shift between s1 and s2
    """
    lagwith = 200
    if not resolution:
        c = np.correlate(s1, s2, mode=2)
        len_s1 = len(s1)
        scale = datarate
    else:
        s1 = interpolate_1d_vector(s1, datarate)
        s2 = interpolate_1d_vector(s2, datarate)
        c = np.correlate(s1, s2, mode=2)
        len_s1 = len(s1)
        scale = datarate*10

    shift = np.linspace(-lagwith, lagwith, 2 * lagwith + 1)
    print("Shift: \n")
    print(shift[0:10])
    # lags = np.arange(-lagwith, lagwith+1)
    corre = c[len_s1 - 1 - lagwith:len_s1 + lagwith]
    maxi = np.argmax(corre)
    print("Maxi: ", maxi, "\n")
    dm1 = abs(corre[maxi] - corre[maxi - 1])
    dp1 = abs(corre[maxi] - corre[maxi + 1])
    if dm1 < dp1:
        x = shift[maxi-2: maxi+1]
        # z = np.polyfit(shift[maxi - 2:maxi + 1], corre[maxi - 2:maxi + 1], 2)
        z = np.polyfit(x, corre[maxi - 2:maxi + 1], 2)
    else:
        z = np.polyfit(shift[maxi - 1:maxi + 2], corre[maxi - 1:maxi + 2], 2)

    dt1 = z[1] / (2 * z[0])

    # return time shift
    return dt1/scale


def shift_frames(gravity: DataFrame, gps: DataFrame, datarate=10) -> DataFrame:
    """
    Synchronize and join a gravity and gps DataFrame (DF) into a single time-shifted DF
    Time lag/shift is found using the find_time_delay function, which cross correlates the
    gravity channel with Eotvos corrections.
    The DFs (gravity and gps) are then upsampled to a 1ms period using cubic interpolation.
    The Gravity DataFrame is then shifted by the time shift factor returned by find_time_delay at ms
    precision.
    We then join the GPS DF on the Gravity DF using a left join resulting in a single DF with
    Gravity and GPS data at 1ms frequency.
    Finally the joined DF is downsampled back to the original frequency (1 or 10 Hz)

    Parameters
    ----------
    gravity: DataFrame
        Gravity data DataFrame to time shift and join
    gps: DataFrame
        GPS/Trajectory DataFrame to correlate with Gravity data
    datarate: int
        Scalar datarate in Hz

    Returns
    -------
    DataFrame:
        Synchronized and joined DataFrame containing set{gravity.columns, gps.columns}
        If gps contains duplicate column names relative to gravity DF, they will be
        suffixed with '_gps'
    """

    eotvos = calc_eotvos(gps['lat'].values, gps['longitude'].values, gps['ell_ht'].values, datarate)
    print("Eotvos: \n")
    print(eotvos[0:5])
    delay = find_time_delay(gravity['gravity'].values, eotvos, 10)
    print(delay)
    time_shift = DateOffset(seconds=delay)

    # Upsample and then shift:
    gravity_1ms = gravity.resample('1L').interpolate(method='cubic').fillna(method='pad')
    gps_1ms = gps.resample('1L').interpolate(method='cubic').fillna(method='pad')
    gravity_synced = gravity_1ms.shift(freq=time_shift)  # type: DataFrame

    # Join shifted dataframes:
    joined = gravity_synced.join(gps_1ms, how='left', rsuffix='_gps')
    # Now downsample back to original period
    down_sample = "{}S".format(1/datarate)
    # TODO: What method to use when downsampling - mean, or select every 10 etc.?
    return joined.resample(down_sample).mean()


def time_Shift_array(s1: np.array,timeshift, datarate: int):
    """
        Time shifting of the input array, by interpolating teh
        original data to a new time query points
        Parameters
        ----------
        s1: np.array
            Input array 1
        tshift: Scalar
                time to shift input array

        Returns
        -------
        Scalar:
            s2: np.array of time shifted data
        """
    t = np.linspace(0, len(s1)/datarate, len(s1))+timeshift
    f = interp1d(t,s1, kind='cubic')
    # only generate data in the range of t2
   # newt = t - timeshift*datarate
    newt = t-timeshift
    for x in range(0, len(t)):
        if newt[x] < t[0]:
            newt[x] = t[0]
        if newt[x] > t[-1]:
            newt[x] = t[-1]
    s2 = f(newt)

    return s2
