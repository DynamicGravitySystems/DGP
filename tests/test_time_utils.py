# coding: utf-8
import os
import unittest
from datetime import datetime
import pandas as pd

from .context import dgp
from dgp.lib import time_utils as tu

class TestTimeUtils(unittest.TestCase):
    def test_leap_seconds(self):
        # TO DO: Test edge cases
        gpsweek = 1959
        gpsweeksecond = 219698.000
        unixtime = 1500987698  # 2017-07-25 13:01:38+00:00
        dt = datetime.strptime('2017-07-25 13:01:38', '%Y-%m-%d %H:%M:%S')
        expected1 = 18

        date1 = '08-07-2015'
        date2 = '08/07/2015'
        date3 = '08/07-2015'
        expected2 = 17

        res_gps = tu.leap_seconds(week=gpsweek, seconds=gpsweeksecond)
        res_unix = tu.leap_seconds(seconds=unixtime)
        res_datetime = tu.leap_seconds(datetime=dt)
        res_date1 = tu.leap_seconds(date=date1)
        res_date2 = tu.leap_seconds(date=date2, dateformat='%m/%d/%Y')

        self.assertEqual(expected1, res_gps)
        self.assertEqual(expected1, res_unix)
        self.assertEqual(expected1, res_datetime)
        self.assertEqual(expected2, res_date1)
        self.assertEqual(expected2, res_date2)

        with self.assertRaises(ValueError):
            tu.leap_seconds(date=date3)

        with self.assertRaises(ValueError):
            tu.leap_seconds(minutes=dt)

    def test_convert_gps_time(self):
        gpsweek = 1959
        gpsweeksecond = 219698.000
        result = 1500987698  # 2017-07-25 13:01:38+00:00
        test_res = tu.convert_gps_time(gpsweek, gpsweeksecond)
        self.assertEqual(result, test_res)

    def test_datetime_to_sow(self):
        # test single input
        dt = datetime(2017, 9, 7, hour=13)
        expected = (1965, 392400)
        given = tu.datetime_to_sow(dt)
        self.assertEqual(expected, given)

        # test iterable input
        dt_series = pd.Series([dt]*20)
        expected_iter = [expected]*20
        given_iter = tu.datetime_to_sow(dt_series)
        self.assertEqual(expected_iter, given_iter)

    def test_datenum_to_datetime(self):
        pass
        # datenum = 736945.5416667824
        # given = tu.datenum_to_datetime(datenum)
        # expected = datetime(2017, 9, 7, hour=13, microsecond=10000)
        # self.assertEqual(expected, given)
