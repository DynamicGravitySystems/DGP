# coding=utf-8

"""
filters.py
Filter classes

"""

import numpy as np
from numpy import array
from scipy import signal

from dgp.lib.transform import Transform, RegisterTransformClass


@RegisterTransformClass('lpfilterfir')
class Filter(Transform):
    var_list = ['fs', 'fc', 'order', 'wn', 'nyq', 'typ', ('window', 'blackman')]

    def func(self, data, fc, fs, window):
        filter_len = 1 / fc
        nyq = fs / 2.0
        wn = fc / nyq
        N = int(2.0 * filter_len * fs)
        taps = signal.firwin(N, wn, window=window, nyq=nyq)
        filtered_data = signal.filtfilt(taps, 1.0, data, padtype='even', padlen=80)
        return filtered_data

    def describe(self):
        return """Filter type: {typ}
                  Window: {window}
                  Cutoff frequency: {fc} Hz
                  Sample frequency: {fs} Hz
                  Nyquist frequency: {nyq} Hz
                  Normalized frequency: {wn} pi radians / sample
                  Order: {order}
               """.format(typ=self.filtertype, fc=self.fc, fs=self.fs,
                          nyq=self.nyq, order=self.order, wn=self.wn,
                          window=self.window)
