# coding=utf-8

"""
filters.py
Filter classes

"""

from scipy import signal

from dgp.lib.transform import Transform, register_transform_class


@register_transform_class
class FIRlowpassfilter(Transform):
    def func(self, data, *, fc, fs, window='blackman'):
        filter_len = 1 / fc
        nyq = fs / 2.0
        wn = fc / nyq
        N = int(2.0 * filter_len * fs)
        taps = signal.firwin(N, wn, window=window, nyq=nyq)
        filtered_data = signal.filtfilt(taps, 1.0, data, padtype='even', padlen=80)
        return filtered_data
