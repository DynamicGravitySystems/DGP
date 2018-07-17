# -*- coding: utf-8 -*-

"""
Test/Develop Plots using PyQtGraph for high-performance user-interactive plots
within the application.
"""
from datetime import datetime

import pytest
import numpy as np
import pandas as pd
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QWidget, QGraphicsScene, QGraphicsWidget, QGraphicsTextItem
from pyqtgraph import GraphicsLayout, PlotItem, PlotDataItem, LegendItem

from dgp.gui.plotting.backends import GridPlotWidget
from dgp.gui.plotting.plotters import LineSelectPlot
from dgp.gui.plotting.helpers import PolyAxis
from .context import APP


@pytest.fixture
def gravity(gravdata) -> pd.Series:
    return gravdata['gravity']


def test_grid_plot_widget_init():
    gpw = GridPlotWidget(rows=2)
    assert isinstance(gpw, QWidget)
    assert isinstance(gpw, QObject)

    assert isinstance(gpw.centralWidget, GraphicsLayout)

    assert 2 == gpw.rows
    assert 1 == gpw.cols

    assert isinstance(gpw.get_plot(row=0), PlotItem)
    assert isinstance(gpw.get_plot(row=1), PlotItem)
    assert gpw.get_plot(row=2) is None

    p0 = gpw.get_plot(row=0)
    assert isinstance(p0.legend, LegendItem)


def test_grid_plot_widget_make_index(gravdata):
    assert ('gravity', 0, 1) == GridPlotWidget.make_index(gravdata['gravity'].name, 0, 1)

    unnamed_ser = pd.Series(np.zeros(14), name='')
    with pytest.raises(ValueError):
        GridPlotWidget.make_index(unnamed_ser.name, 1, 1)

    upper_ser = pd.Series(np.zeros(14), name='GraVitY')
    assert ('gravity', 2, 0) == GridPlotWidget.make_index(upper_ser.name, 2, 0)


def test_grid_plot_widget_plotting(gravity):
    gpw = GridPlotWidget(rows=2)
    p0: PlotItem = gpw.get_plot(row=0)
    p1: PlotItem = gpw.get_plot(row=1)

    assert 0 == len(p0.dataItems) == len(p1.dataItems)

    assert 'gravity' == gravity.name
    assert isinstance(gravity, pd.Series)

    # Plotting an item should return a reference to the PlotDataItem
    _grav_item0 = gpw.add_series(gravity, row=0)
    assert 1 == len(p0.items)
    assert gravity.equals(gpw.get_series(gravity.name, row=0))
    assert isinstance(_grav_item0, PlotDataItem)
    assert gravity.name in [label.text for _, label in p0.legend.items]

    # Re-plotting an existing series on the same plot should do nothing
    _items_len = len(gpw._items.values())
    gpw.add_series(gravity, row=0)
    assert 1 == len(p0.dataItems)
    assert _items_len == len(gpw._items.values())

    # Allow plotting of a duplicate series to a second plot
    _items_len = len(gpw._items.values())
    gpw.add_series(gravity, row=1)
    assert 1 == len(p1.dataItems)
    assert _items_len + 1 == len(gpw._items.values())

    # Remove series only by name (assuming it can only ever be plotted once)
    # or specify which plot to remove it from?
    gpw.remove_series(gravity.name, row=0)
    assert 0 == len(p0.dataItems)
    key = 0, 0, gravity.name
    assert gpw._series.get(key, None) is None
    assert gpw._items.get(key, None) is None
    assert 'gravity' not in [label.text for _, label in p0.legend.items]

    with pytest.raises(KeyError):
        gpw.remove_series('eotvos', 0, 0)


def test_grid_plot_widget_remove_plotitem(gravity):
    gpw = GridPlotWidget(rows=2)
    p0 = gpw.get_plot(0)
    p1 = gpw.get_plot(1)

    _grav_item0 = gpw.add_series(gravity, 0)
    _grav_item1 = gpw.add_series(gravity, 1)
    assert 1 == len(p0.dataItems) == len(p1.dataItems)
    assert _grav_item0 in p0.dataItems
    assert _grav_item0 in gpw._items.values()

    gpw.remove_plotitem(_grav_item0)
    assert 0 == len(p0.dataItems)
    assert 1 == len(p1.dataItems)
    assert _grav_item0 not in gpw._items.items()
    assert _grav_item0 not in p0.dataItems
    assert gpw._series.get((0, 0, 'gravity'), None) is None

    assert 'gravity' not in [label.text for _, label in p0.legend.items]


def test_grid_plot_widget_find_series(gravity):
    """Test function to find & return all keys for a series identified by name
    e.g. if 'gravity' channel is plotted on plot rows 0 and 1, find_series
    should return a list of key tuples (row, col, name) where the series is
    plotted.
    """
    gpw = GridPlotWidget(rows=3)
    assert 3 == gpw.rows

    gpw.add_series(gravity, 0)
    gpw.add_series(gravity, 2)

    expected = [(gravity.name, 0, 0), (gravity.name, 2, 0)]
    result = gpw.find_series(gravity.name)
    assert expected == result

    _grav_series0 = gpw.get_series(*result[0])
    assert gravity.equals(_grav_series0)


def test_grid_plot_widget_set_xaxis_formatter(gravity):
    """Test that appropriate axis formatters are automatically added based on
    the series index type (numeric or DateTime)
    """
    gpw = GridPlotWidget(rows=2)
    gpw.add_series(gravity, 1)

    p0 = gpw.get_plot(0)
    btm_axis_p0 = p0.getAxis('bottom')
    gpw.set_xaxis_formatter(formatter='datetime', row=0)
    assert isinstance(btm_axis_p0, PolyAxis)
    assert btm_axis_p0.timeaxis

    p1 = gpw.get_plot(1)
    btm_axis_p1 = p1.getAxis('bottom')
    assert isinstance(btm_axis_p1, PolyAxis)
    assert not btm_axis_p1.timeaxis

    gpw.set_xaxis_formatter(formatter='scalar', row=0)
    assert not p0.getAxis('bottom').timeaxis


def test_grid_plot_widget_sharex(gravity):
    """Test linked vs unlinked x-axis scales"""
    gpw_unlinked = GridPlotWidget(rows=2, sharex=False)

    gpw_unlinked.add_series(gravity, 0)
    up0_xlim = gpw_unlinked.get_xlim(row=0)
    up1_xlim = gpw_unlinked.get_xlim(row=1)

    assert up1_xlim == [0, 1]
    assert up0_xlim != up1_xlim
    gpw_unlinked.set_xlink(True)
    assert gpw_unlinked.get_xlim(row=0) == gpw_unlinked.get_xlim(row=1)
    gpw_unlinked.set_xlink(False, autorange=True)
    gpw_unlinked.add_series(pd.Series(np.random.rand(len(gravity)),
                                      name='rand'), 1)
    assert gpw_unlinked.get_xlim(row=0) != gpw_unlinked.get_xlim(row=1)

    gpw_linked = GridPlotWidget(rows=2, sharex=True)
    gpw_linked.add_series(gravity, 0)
    assert gpw_linked.get_xlim(row=0) == gpw_linked.get_xlim(row=1)


def test_grid_plot_iterator():
    """Test plots generator property for iterating through all plots"""
    gpw = GridPlotWidget(rows=5)
    count = 0
    for i, plot in enumerate(gpw.plots):
        assert isinstance(plot, PlotItem)
        plot_i = gpw.get_plot(i, 0)
        assert plot_i == plot
        count += 1

    assert gpw.rows == count


def test_grid_plot_clear(gravdata):
    """Test clearing all series from all plots, or selectively"""
    gpw = GridPlotWidget(rows=3)
    gpw.add_series(gravdata['gravity'], 0)
    gpw.add_series(gravdata['long_accel'], 1)
    gpw.add_series(gravdata['cross_accel'], 2)

    assert 3 == len(gpw._items)
    p0 = gpw.get_plot(0, 0)
    assert 1 == len(p0.dataItems)

    gpw.clear()

    assert 0 == len(gpw._items)
    assert 0 == len(p0.dataItems)

    # TODO: Selective clear not yet implemented


def test_PolyAxis_tickStrings():
    axis = PolyAxis(orientation='bottom')
    axis.timeaxis = True
    _scale = 1.0
    _spacing = pd.Timedelta(seconds=1).value

    _HOUR_SEC = 3600
    _DAY_SEC = 86400

    dt_index = pd.DatetimeIndex(start=datetime(2018, 6, 15, 12, 0, 0), freq='s',
                                periods=8*_DAY_SEC)
    dt_list = pd.to_numeric(dt_index).tolist()

    # Test with no values passed
    assert [] == axis.tickStrings([], _scale, 1)

    # If the plot range is <= 60 seconds, ticks should be formatted as %M:%S
    _minute = 61
    expected = [pd.to_datetime(dt_list[i]).strftime('%M:%S') for i in range(_minute)]
    print(f'last expected: {expected[-1]}')
    assert expected == axis.tickStrings(dt_list[:_minute], _scale, _spacing)

    # If 1 minute < plot range <= 1 hour, ticks should be formatted as %H:%M
    _hour = 60*60 + 1
    expected = [pd.to_datetime(dt_list[i]).strftime('%H:%M') for i in range(0, _hour, 5)]
    assert expected == axis.tickStrings(dt_list[:_hour:5], _scale, _spacing)

    # If 1 hour < plot range <= 1 day, ticks should be formatted as %d %H:%M
    tick_values = [dt_list[i] for i in range(0, 23*_HOUR_SEC, _HOUR_SEC)]
    expected = [pd.to_datetime(v).strftime('%d %H:%M') for v in tick_values]
    assert expected == axis.tickStrings(tick_values, _scale, _HOUR_SEC)

    # If 1 day < plot range <= 1 week, ticks should be formatted as %m-%d %H

    tick_values = [dt_list[i] for i in range(0, 3*_DAY_SEC, _DAY_SEC)]
    expected = [pd.to_datetime(v).strftime('%m-%d %H') for v in tick_values]
    assert expected == axis.tickStrings(tick_values, _scale, _DAY_SEC)


@pytest.mark.skip("Defer implementation of this")
def test_grid_plot_multi_y(gravdata):
    _gravity = gravdata['gravity']
    _longacc = gravdata['long_accel']
    gpw = GridPlotWidget(rows=1, multiy=True)

    gpw.add_series(_gravity, 0)
    gpw.add_series(_longacc, 0, axis='right')
    p0 = gpw.get_plot(0)
    scene: QGraphicsScene = p0.scene()
    print(scene.items())

    assert 1 == len(gpw.get_plot(0).dataItems)


@pytest.mark.skip("Not implemented yet")
def test_line_select_plot_init():
    plot = LineSelectPlot(rows=2)

    assert isinstance(plot, QObject)
    assert isinstance(plot, QWidget)

    assert 2 == plot.rows

