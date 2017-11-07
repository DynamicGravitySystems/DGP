# coding: utf-8

from .context import dgp
from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.eotvos import calc_eotvos
import matplotlib.pyplot as plt
from dgp.lib.trajectory_ingestor import import_trajectory
from dgp.lib.time_utils import convert_gps_time
import numpy as np
from numpy import array
from scipy.signal import correlate, filtfilt, firwin
from dgp.lib.timesync import find_time_delay
import unittest


class Test_Timesync(unittest.TestCase):
    def setUp(self):
        pass

    def test_eotvos_shift(self):
        # generate syntetic data totest
        t1=np.linspace(1,5000,50000)+0.0
        t2=t1+5.258
        r1=np.random.randn(np.size(t1))*0.05
        s1=np.sin(0.8*t1)+np.sin(0.2*t1)
        s2=np.sin(0.8*t2)+np.sin(0.2*t2)
        time=find_time_delay(s1,s2,10)

        self.assertAlmostEqual(5.258, -time, places=2)
