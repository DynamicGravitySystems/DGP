# coding: utf-8
import pytest
from datetime import datetime
import pandas as pd

from dgp.lib import time_utils as tu


def test_leap_seconds():
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

    assert expected1 == res_gps
    assert expected1 == res_unix
    assert expected1 == res_datetime
    assert expected2 == res_date1
    assert expected2 == res_date2

    with pytest.raises(ValueError):
        tu.leap_seconds(date=date3)

    with pytest.raises(ValueError):
        tu.leap_seconds(minutes=dt)


def test_convert_gps_time():
    gpsweek = 1959
    gpsweeksecond = 219698.000
    result = 1500987698  # 2017-07-25 13:01:38+00:00
    test_res = tu.convert_gps_time(gpsweek, gpsweeksecond)
    assert result == test_res


@pytest.mark.parametrize(
    'given_sow, expected_dt', [
        (312030.8, datetime(2017, 3, 22, 14, 40, 30, 800000)),
        (312030.08, datetime(2017, 3, 22, 14, 40, 30, 80000)),
        (312030.008, datetime(2017, 3, 22, 14, 40, 30, 8000)),
        (312030.0008, datetime(2017, 3, 22, 14, 40, 30, 800)),
    ]
)
def test_convert_gps_time_datetime(given_sow, expected_dt):
    gpsweek = pd.Series([1941])
    gpsweeksecond = pd.Series([given_sow])
    result = pd.Series([expected_dt])
    test_res = tu.convert_gps_time(gpsweek, gpsweeksecond, format='datetime')
    assert result.equals(test_res)


def test_datetime_to_sow():
    # test single input
    dt = datetime(2017, 9, 7, hour=13)
    expected = (1965, 392400)
    given = tu.datetime_to_sow(dt)
    assert expected == given

    # test iterable input
    dt_series = pd.Series([dt]*20)
    expected_iter = [expected]*20
    given_iter = tu.datetime_to_sow(dt_series)
    assert expected_iter == given_iter
