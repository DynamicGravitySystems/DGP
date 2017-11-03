# coding=utf-8
# This file is part of DynamicGravityProcessor (https://github.com/DynamicGravitySystems/DGP).
import numpy as np
import scipy.interpolate
import matplotlib.pyplot as plt

def interpolate_1d_vector(vector, factor):
    """
    Interpolate, i.e. upsample, a given 1D vector by a specific interpolation factor.
    :param vector: 1D data vector
    :param factor: factor for interpolation (must be integer)
    :return: interpolated 1D vector by a given factor
    """
    x = np.arange(np.size(vector))
    y = vector
    f = scipy.interpolate.interp1d(x, y)

    x_extended_by_factor = np.linspace(x[0], x[-1], np.size(x) * factor)
    y_interpolated = np.zeros(np.size(x_extended_by_factor))

    i = 0
    for x in x_extended_by_factor:
        y_interpolated[i] = f(x)
        i += 1

    return y_interpolated

def find_time_delay(s1,s2,datarate,resolution=None):
    """
        Python implementacion of Daniel Aliod time syncronization matlab function
        Find the time shift or dalay between to arrays.If s1 is avanced to s2 timedelay is psitive
        :param array: s1 is 1D array
        :param array: s2 1D array
        :param datarate: Scalar data sampling rate in Hz
        :param resolution: if None , uses data without oversampling
        :return: time shift between s1 and s2
        """
    lagwith = 200
    if resolution is None:
        out = plt.xcorr(s1,s2, maxlags=lagwith)
        scale=datarate
    else:
        is1 = interpolate_1d_vector(s1,datarate)
        is2 = interpolate_1d_vector(s2,datarate)
        out = plt.xcorr(is2,is1, maxlags=lagwith)
        scale=datarate*10
    shift = np.linspace(-lagwith, lagwith, 2 * lagwith + 1)
    corre = out[1]
    maxi = np.argmax(corre)
    dm1 = abs(corre[maxi] - corre[maxi - 1])
    dp1 = abs(corre[maxi] - corre[maxi + 1])
    if dm1 < dp1:
        z = np.polyfit(shift[maxi - 2:maxi + 1], corre[maxi - 2:maxi + 1], 2)
    else:
        z = np.polyfit(shift[maxi - 1:maxi + 2], corre[maxi - 1:maxi + 2], 2)

    dt1 = z[1] / (2 * z[0])
    #print(dt1 / scale)
    # return time shift
    return dt1/scale