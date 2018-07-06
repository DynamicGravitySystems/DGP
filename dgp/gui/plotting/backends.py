# -*- coding: utf-8 -*-

from itertools import cycle
from typing import List

import pandas as pd
from pyqtgraph.widgets.GraphicsView import GraphicsView
from pyqtgraph.graphicsItems.GraphicsLayout import GraphicsLayout
from pyqtgraph.widgets.PlotWidget import PlotItem
from pyqtgraph import SignalProxy

from .helpers import DateAxis

"""
Rationale for StackedMPLWidget and StackedPGWidget:
Each of these classes should act as a drop-in replacement for the other, 
presenting as a single widget that can be added to a Qt Layout.
Both of these classes are designed to create a variable number of plots 
'stacked' on top of each other - as in rows.
MPLWidget will thus contain a series of Axes classes which can be used to 
plot on
PGWidget will contain a series of PlotItem classes which likewise can be used to 
plot.

It remains to be seen if the Interface/ABC AbstractSeriesPlotter and its descendent 
classes PlotWidgetWrapper and MPLAxesWrapper are necessary - the intent of 
these classes was to wrap a PlotItem or Axes and provide a unified standard 
interface for plotting. However, the Stacked*Widget classes might nicely 
encapsulate what was intended there.
"""
__all__ = ['PyQtGridPlotWidget']


class PyQtGridPlotWidget(GraphicsView):
    # TODO: Use multiple Y-Axes to plot 2 lines of different scales
    # See pyqtgraph/examples/MultiplePlotAxes.py
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    colorcycle = cycle([{'color': v} for v in colors])

    def __init__(self, rows=1, cols=1, background='w', grid=True,
                 sharex=True, sharey=False, tickFormatter='date', parent=None):
        super().__init__(parent=parent, background=background)
        self._gl = GraphicsLayout(parent=parent)
        self.setCentralItem(self._gl)
        self._plots = []  # type: List[PlotItem]
        self._lines = {}
        # Store ref to signal proxies so they are not GC'd
        self._sigproxies = []

        for row in range(rows):
            for col in range(cols):
                plot_kwargs = dict(row=row, col=col, background=background)
                if tickFormatter == 'date':
                    date_fmtr = DateAxis(orientation='bottom')
                    plot_kwargs['axisItems'] = {'bottom': date_fmtr}
                plot = self._gl.addPlot(**plot_kwargs)
                plot.getAxis('left').setWidth(40)

                if len(self._plots) > 0:
                    if sharex:
                        plot.setXLink(self._plots[0])
                    if sharey:
                        plot.setYLink(self._plots[0])

                plot.showGrid(x=grid, y=grid)
                plot.addLegend(offset=(-15, 15))
                self._plots.append(plot)

    @property
    def plots(self):
        return self._plots

    def __len__(self):
        return len(self._plots)

    def add_series(self, series: pd.Series, idx=0, formatter='date', *args, **kwargs):
        # TODO why not get rid of the wrappers and perfrom the functionality here
        # Remove a layer of confusing indirection
        # return self._wrapped[idx].add_series(series, *args, **kwargs)
        plot = self._plots[idx]
        sid = id(series)
        if sid in self._lines:
            # Constraint - allow line on only 1 plot at a time
            self.remove_series(series)

        xvals = pd.to_numeric(series.index, errors='coerce')
        yvals = pd.to_numeric(series.values, errors='coerce')
        line = plot.plot(x=xvals, y=yvals, name=series.name, pen=next(self.colorcycle))
        self._lines[sid] = line
        return line

    def remove_series(self, series: pd.Series):
        # TODO: As above, remove the wrappers, do stuff here
        sid = id(series)
        if sid not in self._lines:

            return
        for plot in self._plots:  # type: PlotItem
            plot.legend.removeItem(self._lines[sid].name())
            plot.removeItem(self._lines[sid])
        del self._lines[sid]

    def clear(self):
        """Clear all lines from all plots"""
        for sid in self._lines:
            for plot in self._plots:
                plot.legend.removeItem(self._lines[sid].name())
                plot.removeItem(self._lines[sid])

        self._lines = {}


    def add_onclick_handler(self, slot, rateLimit=60):
        sp = SignalProxy(self._gl.scene().sigMouseClicked, rateLimit=rateLimit,
                         slot=slot)
        self._sigproxies.append(sp)
        return sp

    def get_xlim(self, index=0):
        return self._plots[index].vb.viewRange()[0]

    def get_ylim(self, index=0):
        return self._plots[index].vb.viewRange()[1]

    def get_plot(self, row):
        return self._plots[row]

