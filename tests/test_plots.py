# -*- coding: utf-8 -*-

"""
Test/Develop Plots using PyQtGraph for high-performance user-interactive plots
within the application.
"""
from datetime import datetime

import pytest
import numpy as np
import pandas as pd
from PyQt5.QtCore import QObject, QEvent, QPointF, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtTest import QSignalSpy
from PyQt5.QtWidgets import QWidget, QGraphicsScene, QGraphicsSceneMouseEvent
from pyqtgraph import GraphicsLayout, PlotItem, PlotDataItem, LegendItem, Point
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent

from dgp.core.oid import OID
from dgp.core.types.tuples import LineUpdate
from dgp.gui.plotting.backends import GridPlotWidget
from dgp.gui.plotting.plotters import LineSelectPlot
from dgp.gui.plotting.helpers import PolyAxis, LinearFlightRegion
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
    assert ('gravity', 0, 1, 'left') == GridPlotWidget.make_index(gravdata['gravity'].name, 0, 1)

    unnamed_ser = pd.Series(np.zeros(14), name='')
    with pytest.raises(ValueError):
        GridPlotWidget.make_index(unnamed_ser.name, 1, 1)

    upper_ser = pd.Series(np.zeros(14), name='GraVitY')
    assert ('gravity', 2, 0, 'left') == GridPlotWidget.make_index(upper_ser.name, 2, 0)

    assert ('long_acc', 3, 1, 'left') == GridPlotWidget.make_index('long_acc', 3, 1, 'sideways')


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

    expected = [(gravity.name, 0, 0, 'left'), (gravity.name, 2, 0, 'left')]
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


def test_grid_plot_multi_y(gravdata):
    _gravity = gravdata['gravity']
    _longacc = gravdata['long_accel']
    gpw = GridPlotWidget(rows=1, multiy=True)

    p0 = gpw.get_plot(0)
    gpw.add_series(_gravity, 0)
    gpw.add_series(_longacc, 0, axis='right')

    # Legend entry for right axis should appear on p0 legend
    assert _gravity.name in [label.text for _, label in p0.legend.items]
    assert _longacc.name in [label.text for _, label in p0.legend.items]

    assert 1 == len(gpw.get_plot(0).dataItems)
    assert 1 == len(gpw.get_plot(0, axis='right').dataItems)

    assert gpw.get_xlim(0) == gpw.get_plot(0, axis='right').vb.viewRange()[0]



def test_LineSelectPlot_init():
    plot = LineSelectPlot(rows=2)

    assert isinstance(plot, QObject)
    assert isinstance(plot, QWidget)

    assert 2 == plot.rows


def test_LineSelectPlot_selection_mode():
    plot = LineSelectPlot(rows=3)
    assert not plot.selection_mode
    plot.selection_mode = True
    assert plot.selection_mode

    plot.add_segment(datetime.now().timestamp(),
                     datetime.now().timestamp() + 1000)

    assert 1 == len(plot._segments)

    for lfr_grp in plot._segments.values():
        for lfr in lfr_grp:  # type: LinearFlightRegion
            assert lfr.movable

    plot.selection_mode = False
    for lfr_grp in plot._segments.values():
        for lfr in lfr_grp:
            assert not lfr.movable


def test_LineSelectPlot_add_segment():
    _rows = 2
    plot = LineSelectPlot(rows=_rows)
    update_spy = QSignalSpy(plot.segment_changed)

    ts_oid = OID(tag='datetime_timestamp')
    ts_start = datetime.now().timestamp() - 1000
    ts_stop = ts_start + 200

    pd_oid = OID(tag='pandas_timestamp')
    pd_start = pd.Timestamp.now()
    pd_stop = pd_start + pd.Timedelta(seconds=1000)

    assert 0 == len(plot._segments)

    plot.add_segment(ts_start, ts_stop, ts_oid)
    assert 1 == len(update_spy)
    assert 1 == len(plot._segments)
    lfr_grp = plot._segments[ts_oid]
    assert _rows == len(lfr_grp)

    # Test adding segment using pandas.Timestamp values
    plot.add_segment(pd_start, pd_stop, pd_oid)
    assert 2 == len(update_spy)
    assert 2 == len(plot._segments)
    lfr_grp = plot._segments[pd_oid]
    assert _rows == len(lfr_grp)


def test_LineSelectPlot_remove_segment():
    _rows = 2
    plot = LineSelectPlot(rows=_rows)
    update_spy = QSignalSpy(plot.segment_changed)

    lfr_oid = OID(tag='segment selection')
    lfr_start = datetime.now().timestamp()
    lfr_end = lfr_start + 300

    plot.add_segment(lfr_start, lfr_end, lfr_oid)
    assert 1 == len(update_spy)
    assert isinstance(update_spy[0][0], LineUpdate)

    assert 1 == len(plot._segments)
    segments = plot._segments[lfr_oid]
    assert segments[0] in plot.get_plot(row=0).items
    assert segments[1] in plot.get_plot(row=1).items

    assert lfr_oid == segments[0].group
    assert lfr_oid == segments[1].group

    with pytest.raises(TypeError):
        plot.remove_segment("notavalidtype")

    plot.remove_segment(segments[0])
    assert 0 == len(plot._segments)


def test_LineSelectPlot_check_proximity(gravdata):
    _rows = 2
    plot = LineSelectPlot(rows=_rows)
    print(f'plot geom: {plot.geometry()}')
    print(f'scene rect: {plot.sceneRect()}')
    p0 = plot.get_plot(0)
    plot.add_series(gravdata['gravity'], 0)

    lfr_start = gravdata.index[0]
    lfr_end = gravdata.index[2]
    p0xlim = plot.get_xlim(0)
    span = p0xlim[1] - p0xlim[0]

    xpos = gravdata.index[3].value
    assert plot._check_proximity(xpos, span)

    plot.add_segment(lfr_start, lfr_end)

    assert not plot._check_proximity(xpos, span, proximity=0.2)
    xpos = gravdata.index[4].value
    assert plot._check_proximity(xpos, span, proximity=0.2)





