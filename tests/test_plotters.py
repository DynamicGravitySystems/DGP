# coding: utf-8

import unittest
from pathlib import Path

from matplotlib.dates import date2num
from matplotlib.lines import Line2D

from dgp.lib.types import DataSource, DataChannel
from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.enums import DataTypes
from dgp.gui.plotting.mplutils import StackedAxesManager, _pad, COLOR_CYCLE
from dgp.gui.plotting.plotters import BasePlottingCanvas


class MockDataSource(DataSource):
    def __init__(self, data, uid, filename, fields, dtype, x0, x1):
        super().__init__(uid, filename, fields, dtype, x0, x1)
        self._data = data

    # Patch load func to remove dependence on HDF5 storage for test
    def load(self, field=None):
        if field is not None:
            return self._data[field]
        return self._data


class BasicPlotter(BasePlottingCanvas):
    def __init__(self, rows):
        super().__init__()
        self.axmgr = StackedAxesManager(self.figure, rows=rows)


class TestPlotters(unittest.TestCase):
    def setUp(self):
        grav_path = Path('tests/sample_data/test_data.csv')
        self.df = read_at1a(str(grav_path))
        x0 = self.df.index.min()
        x1 = self.df.index.max()
        self.dsrc = MockDataSource(self.df, 'abc', grav_path.name,
                                   self.df.keys(), DataTypes.GRAVITY, x0, x1)
        self.grav_ch = DataChannel('gravity', self.dsrc)
        self.cross_ch = DataChannel('cross', self.dsrc)
        self.long_ch = DataChannel('long', self.dsrc)
        self.plotter = BasicPlotter(rows=2)
        self.mgr = self.plotter.axmgr

    def test_magic_methods(self):
        """Test __len__ __contains__ __getitem__ methods."""
        # Test count of Axes
        self.assertEqual(2, len(self.mgr))

        # TODO: __contains__ in mgr changed to check Axes
        grav_uid = self.mgr.add_series(self.grav_ch.series(), row=0)
        # self.assertIn(grav_uid, self.mgr)

        # Be aware that the __getitem__ returns a tuple of (Axes, Axes)
        self.assertEqual(self.mgr.get_axes(0, twin=False), self.mgr[0][0])

    def test_min_max(self):
        x0, x1 = self.dsrc.get_xlim()
        x0_num = date2num(x0)
        x1_num = date2num(x1)
        self.assertIsInstance(x0_num, float)
        self.assertEqual(736410.6114664351, x0_num)
        self.assertIsInstance(x1_num, float)
        self.assertEqual(736410.6116793981, x1_num)

        # Y-Limits are local to the x-span of the data being viewed.
        # As such I don't think it makes sense to store the ylim value within
        # the data source

        # self.assertIsNone(self.grav_ch._ylim)
        # y0, y1 = self.grav_ch.get_ylim()
        # self.assertEqual((y0, y1), self.grav_ch._ylim)

        # grav = self.df['gravity']
        # _y0 = grav.min()
        # _y1 = grav.max()
        # self.assertEqual(_y0, y0)
        # self.assertEqual(_y1, y1)

    def test_axmgr_workflow(self):
        """Test adding and removing series to/from the AxesManager
        Verify correct setting of x/y plot limits."""
        ax = self.mgr.get_axes(0, twin=False)
        twin = self.mgr.get_axes(0, twin=True)

        # ADD 1
        uid_1 = self.mgr.add_series(self.grav_ch.series(), row=0)
        self.assertEqual(1, uid_1)
        self.assertEqual(1, len(ax.lines))
        self.mgr.remove_series(uid_1)
        self.assertEqual(0, len(ax.lines))
        self.assertEqual((-1, 1), ax.get_ylim())

        # Test margin setting method which adds 5% padding to view of data
        left, right = self.grav_ch.get_xlim()
        left, right = _pad(date2num(left), date2num(right), self.mgr._padding)
        self.assertEqual((left, right), ax.get_xlim())

        # Series should be added to primary axes here as last line was removed
        self.assertEqual(0, len(ax.lines))
        # ADD 2
        uid_2 = self.mgr.add_series(self.grav_ch.series(), row=0,
                                    uid=self.grav_ch.uid)
        self.assertEqual(self.grav_ch.uid, uid_2)
        self.assertEqual(0, len(twin.lines))
        self.assertEqual(1, len(ax.lines))

        # ADD 3
        uid_3 = self.mgr.add_series(self.cross_ch.series(), row=0)
        line_3 = self.mgr._lines[uid_3]  # type: Line2D
        self.assertEqual(COLOR_CYCLE[2], line_3.get_color())

        # Add 1 to row 2 - Verify independent color cycling
        uid_4 = self.mgr.add_series(self.grav_ch.series(), row=1)
        line_4 = self.mgr._lines[uid_4]
        self.assertEqual(COLOR_CYCLE[0], line_4.get_color())

        # Test attempt to remove invalid UID
        with self.assertRaises(ValueError):
            self.mgr.remove_series('uid_invalid', 7, 12, uid_3)

    def test_reset_view(self):
        """Test view limit functionality when resetting view (home button)"""
        # Zoom Box ((x0, x1), (y0, y1))
        zoom_area = ((500, 600), (-1, 0.5))

        data = self.grav_ch.series()
        data_x = date2num(data.index.min()), date2num(data.index.max())
        data_y = data.min(), data.max()

        data_uid = self.mgr.add_series(data, row=0)
        ax0 = self.mgr.get_axes(0, twin=False)
        self.assertEqual(1, len(ax0.lines))

        ax0.set_xlim(*zoom_area[0])
        ax0.set_ylim(*zoom_area[1])
        self.assertEqual(zoom_area[0], ax0.get_xlim())
        self.assertEqual(zoom_area[1], ax0.get_ylim())

        self.mgr.reset_view()
        # Assert view limits are equal to data limits + 5% padding after reset
        self.assertEqual(_pad(*data_x), ax0.get_xlim())
        self.assertEqual(_pad(*data_y), ax0.get_ylim())

        self.mgr.remove_series(data_uid)
        self.assertEqual((-1.0, 1.0), ax0.get_ylim())

        # Test reset_view with no lines plotted
        self.mgr.reset_view()
