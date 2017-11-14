# coding=utf-8

# This file is part of DynamicGravityProcessor (https://github.com/DynamicGravitySystems/DGP).

import numpy as np
from scipy.interpolate import interp1d

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


def find_time_delay(s1: np.array, s2: np.array, datarate: int, resolution: bool=None):
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
    # lags = np.arange(-lagwith, lagwith+1)
    corre = c[len_s1 - 1 - lagwith:len_s1 + lagwith]
    maxi = np.argmax(corre)
    dm1 = abs(corre[maxi] - corre[maxi - 1])
    dp1 = abs(corre[maxi] - corre[maxi + 1])
    if dm1 < dp1:
        z = np.polyfit(shift[maxi - 2:maxi + 1], corre[maxi - 2:maxi + 1], 2)
    else:
        z = np.polyfit(shift[maxi - 1:maxi + 2], corre[maxi - 1:maxi + 2], 2)

    dt1 = z[1] / (2 * z[0])

    # return time shift
    return dt1/scale

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