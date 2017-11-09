# coding: utf-8

from .context import dgp

import unittest

import numpy as np

from dgp.lib.timesync import find_time_delay


class TestTimesync(unittest.TestCase):
    def test_timedelay(self):
        # Generate synthetic data to test find_time_delay function
        t1 = np.linspace(1, 5000, 50000)+0.0
        t2 = t1+5.258
        # r1 = np.random.randn(np.size(t1))*0.05
        s1 = np.sin(0.8*t1)+np.sin(0.2*t1)
        s2 = np.sin(0.8*t2)+np.sin(0.2*t2)
        time = find_time_delay(s1, s2, 10)

        self.assertAlmostEqual(5.258, -time, places=2)
