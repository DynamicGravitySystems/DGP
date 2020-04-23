# coding: utf-8

from scipy import signal
import pandas as pd
import numpy as np


# TODO: Add Gaussian filter
# TODO: Add B-spline
# TODO: Move detrend

def lp_filter(data_in, filter_len=100, fs=1):
    fc = 1 / filter_len
    nyq = fs / 2
    wn = fc / nyq
    n = int(2 * filter_len * fs)
    taps = signal.firwin(n, wn, window='blackman')
    filtered_data = signal.filtfilt(taps, 1.0, data_in, padtype='even',
                                    padlen=80)
    name = 'filt_blackman_' + str(filter_len)
    return pd.Series(filtered_data, index=data_in.index, name=name)


def bw_filter(data_in, filter_len=70, n=2):
    wn = 1 / (filter_len / np.nanmean(np.diff(data_in.index).astype(float) / 1e9))
    B, A = signal.butter(n, wn, output='ba')
    data_in.interpolate(method='cubic', axis=0, inplace=True)
    filtered_data = signal.filtfilt(B, A, data_in, method='gust')
    name = 'filt_butterworth_' + str(filter_len)
    return pd.Series(filtered_data, index=data_in.index, name=name)


def sg_filter(data_in, filter_len=100):
    wn = 3 * filter_len / np.nanmean(np.diff(data_in.index).astype(float) / 1e9) + 1
    filtered_data = signal.savgol_filter(data_in, wn, 5, mode='nearest')
    name = 'filt_savgol_' + str(filter_len)
    return pd.Series(filtered_data, index=data_in.index, name=name)


def detrend(data_in, begin, end):
    # TODO: Do ndarrays with both dimensions greater than 1 work?

    # TODO: Duck type this check?
    if isinstance(data_in, pd.DataFrame):
        length = len(data_in.index)
    else:
        length = len(data_in)

    trend = np.linspace(begin, end, num=length)
    if isinstance(data_in, (pd.Series, pd.DataFrame)):
        trend = pd.Series(trend, index=data_in.index)
        result = data_in.sub(trend, axis=0)
    else:
        result = data_in - trend
    return result
