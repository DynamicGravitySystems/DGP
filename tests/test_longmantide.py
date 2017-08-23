from .context import dgp
from dgp.lib import longmantide as lt

import unittest
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import os.path

class TestLongmanTide(unittest.TestCase):

    def test_basic(self):
        lat = 40.7914  # Station Latitude
        lon = 282.1414  # Station Longitude
        alt = 370.  # Station Altitude [meters]
        # model = lt.TideModel()  # Make a model object
        time = datetime(2015, 4, 23, 0, 0, 0)  # When we want the tide
        gm, gs, g = lt.solve_longman(lat, lon, alt, time)
        np.testing.assert_almost_equal(gm, 0.0324029651226, 8)
        np.testing.assert_almost_equal(gs, -0.0288682178454, 8)
        np.testing.assert_almost_equal(g, 0.00353474727722, 8)

    def test_series(self):
        lat = pd.Series(data=np.full(5, 40.7914))
        lon = pd.Series(data=np.full(5, 282.1414))
        alt = pd.Series(data=np.full(5, 370.))

        # model = lt.TideModel()
        time = pd.DatetimeIndex(data=[datetime(2015, 4, 23, 0, 0, 0)]*5)
        gm, gs, g = lt.solve_longman(lat, lon, alt, time)

        gm_expect = np.full(5, 0.0324029651226)
        gs_expect = np.full(5, -0.0288682178454)
        g_expect = np.full(5, 0.00353474727722)

        np.testing.assert_array_almost_equal(gm, gm_expect, 8)
        np.testing.assert_array_almost_equal(gs, gs_expect, 8)
        np.testing.assert_array_almost_equal(g, g_expect, 8)

    def test_against_matlab(self):
        filepath = os.path.abspath('./tide_test_data.csv')
        df = pd.read_csv(filepath, skiprows=1)
        df.columns = ['lat', 'lon', 'num_time', 'total']

        df.index = (df['num_time'].astype(int).map(datetime.fromordinal) +
                    pd.to_timedelta(df['num_time'] % 1, unit='D') -
                    pd.to_timedelta('366 days'))

        df['alt'] = pd.Series(np.full(len(df.index), 0.0), index=df.index)
        gm, gs, g = lt.solve_longman(df['lat'], df['lon'], df['alt'], df.index)

        np.testing.assert_array_almost_equal(g, df['total'])
