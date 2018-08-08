# coding: utf-8

import unittest
import numpy as np
import pandas as pd

from dgp.lib.timesync import find_time_delay, shift_frame


class TestTimesync(unittest.TestCase):
    def test_timedelay_array(self):
        rnd_offset = 1.1
        t1 = np.arange(0, 5000, 0.1, dtype=np.float64)
        t2 = t1 + rnd_offset
        s1 = np.sin(0.8 * t1) + np.sin(0.2 * t1)
        s2 = np.sin(0.8 * t2) + np.sin(0.2 * t2)
        time = find_time_delay(s1, s2, 10)
        self.assertAlmostEqual(rnd_offset, -time, places=2)

    def test_timedelay_timelike_index(self):
        rnd_offset = 1.1
        now = pd.Timestamp.now()
        t1 = np.arange(0, 5000, 0.1, dtype=np.float64)
        index1 = pd.to_timedelta(t1, unit='s') + now
        t2 = t1 + rnd_offset
        index2 = pd.to_timedelta(t2, unit='s') + now
        s1 = np.sin(0.8 * t1) + np.sin(0.2 * t1)
        frame1 = pd.Series(s1, index=index1)
        s2 = np.sin(0.8 * t2) + np.sin(0.2 * t2)
        frame2 = pd.Series(s2, index=index2)

        time = find_time_delay(frame1, frame2)
        self.assertAlmostEqual(rnd_offset, -time, places=2)

    def test_timedelay_warning(self):
        rnd_offset = 1.1

        t1 = np.arange(0, 5000, 0.1, dtype=np.float64)
        t2 = t1 + rnd_offset

        s1 = np.sin(0.8 * t1) + np.sin(0.2 * t1)
        index = pd.Timestamp.now() + pd.to_timedelta(t1, unit='s')
        frame = pd.Series(s1, index=index)
        s2 = np.sin(0.8 * t2) + np.sin(0.2 * t2)

        with self.assertWarns(UserWarning):
            find_time_delay(frame, s2)

    def test_timedelay_ignore_indexes(self):
        rnd_offset = 1.1
        t1 = np.arange(0, 5000, 0.1, dtype=np.float64)
        t2 = t1 + rnd_offset
        s1 = np.sin(0.8 * t1) + np.sin(0.2 * t1)
        s2 = np.sin(0.8 * t2) + np.sin(0.2 * t2)
        now = pd.Timestamp.now()
        index1 = now + pd.to_timedelta(t1, unit='s')
        frame1 = pd.Series(s1, index=index1)
        frame2 = s2

        msg_expected = 's2 has no index. Ignoring index for s1.'
        with self.assertWarns(UserWarning, msg=msg_expected):
            find_time_delay(frame1, frame2)

        frame1 = s1
        index2 = now + pd.to_timedelta(t2, unit='s')
        frame2 = pd.Series(s2, index=index2)

        msg_expected = 's1 has no index. Ignoring index for s2.'
        with self.assertWarns(UserWarning, msg=msg_expected):
            find_time_delay(frame1, frame2)

        frame1 = pd.Series(s1, index=index1)
        index2 = now + pd.to_timedelta(t2, unit='s')
        frame2 = pd.Series(s2)

        msg_expected = ('Index of s2 is not a DateTimeIndex. Ignoring both '
                        'indexes.')
        with self.assertWarns(UserWarning, msg=msg_expected):
            find_time_delay(frame1, frame2)

        frame1 = pd.Series(s1)
        index2 = now + pd.to_timedelta(t2, unit='s')
        frame2 = pd.Series(s2, index=index2)

        msg_expected = ('Index of s1 is not a DateTimeIndex. Ignoring both '
                        'indexes.')
        with self.assertWarns(UserWarning, msg=msg_expected):
            find_time_delay(frame1, frame2)

    def test_timedelay_exceptions(self):
        rnd_offset = 1.1
        now = pd.Timestamp.now()
        t1 = np.arange(0, 5000, 0.1, dtype=np.float64)
        index1 = pd.to_timedelta(t1, unit='s') + now
        t2 = np.arange(0, 5000, 0.12, dtype=np.float64) + rnd_offset
        index2 = pd.to_timedelta(t2, unit='s') + now
        s1 = np.sin(0.8 * t1) + np.sin(0.2 * t1)
        frame1 = pd.Series(s1, index=index1)
        s2 = np.sin(0.8 * t2) + np.sin(0.2 * t2)
        frame2 = pd.Series(s2, index=index2)

        msg_expected = 'Indexes have different frequencies'
        with self.assertRaises(ValueError, msg=msg_expected):
            find_time_delay(frame1, frame2)

    def test_shift_frame(self):
        test_input = pd.Series(np.arange(10))
        index = pd.Timestamp.now() + pd.to_timedelta(np.arange(10), unit='s')
        test_input.index = index
        shifted_index = index.shift(110, freq='L')
        expected = test_input.copy()
        expected.index = shifted_index

        res = shift_frame(test_input, 0.11)
        self.assertTrue(res.equals(expected))
