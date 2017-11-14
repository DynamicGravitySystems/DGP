# coding: utf-8

from .context import dgp

import unittest

import numpy as np

from dgp.lib.timesync import find_time_delay,time_Shift_array


class TestTimesync(unittest.TestCase):
    def test_timedelay(self):
        # Generate synthetic data to test find_time_delay function
        rnd_offset=1.1
        t1 = np.linspace(1, 5000, 50000)+0.0
        t2 = t1+rnd_offset
        # r1 = np.random.randn(np.size(t1))*0.05
        s1 = np.sin(0.8*t1)+np.sin(0.2*t1)
        s2 = np.sin(0.8*t2)+np.sin(0.2*t2)
        time = find_time_delay(s1, s2, 10)
        self.assertAlmostEqual(rnd_offset, -time, places=2)

       #

    def test_timeshift(self):
        rnd_offset = 6.234
        # generate syntetic data totest
        t1 = np.linspace(0, 5000, 50000) + 0.0
        t2 = t1 + rnd_offset

        r1 = np.random.randn(np.size(t1)) * 0.05
        s1 = 20000 * np.sin(0.2 * t1) + 2000 * np.sin(0.8 * t1)
        s2 = 20000 * np.sin(0.2 * t2) + 2000 * np.sin(0.8 * t2)
        """""
        f = interp1d(t2,s2,kind='cubic')
        # only generate data in the range of t2
        newt=t2-6.258
        for x in range(0,len(t2)):
            if newt[x]<t2[0]:
                newt[x]=t2[0]
            if newt[x]>t2[-1]:
                newt[x]=t2[-1]
        s3 = f(newt)
        """
        s3 = time_Shift_array(s2,rnd_offset, 10)
        """""
        error1=s1-s2
        plt.figure()
        plt.title('Signal error no comp')
        plt.plot(t2,error1)
        """
        error2 = s1 - s3
        """"

        plt.figure()
        plt.title('Signal compensated')
        plt.plot(t2[100:len(t2)-100],error2[100:len(t2)-100],'red')
        plt.show()
        """""
        outsig = np.std(error2[100:len(t2) - 100])
        print('std of error', outsig)

        self.assertAlmostEqual(0,outsig, places=2)
        #


