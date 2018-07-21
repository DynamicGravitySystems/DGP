# -*- coding: utf-8 -*-

from itertools import cycle
from typing import List, Union, Tuple, Generator, Dict

import pandas as pd
from pyqtgraph.widgets.GraphicsView import GraphicsView
from pyqtgraph.graphicsItems.GraphicsLayout import GraphicsLayout
from pyqtgraph.widgets.PlotWidget import PlotItem
from pyqtgraph import SignalProxy, PlotDataItem, ViewBox

from .helpers import DateAxis, PolyAxis

__all__ = ['GridPlotWidget', 'PyQtGridPlotWidget']

LINE_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
               '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']


class LinkedPlotItem(PlotItem):
    """LinkedPlotItem simplifies the creation of a second plot axes linked to
    the right axis scale of the base :class:`PlotItem`

    This class is used by GridPlotWidget to construct plots which have a second
    y-scale in order to display two (or potentially more) Series on the same
    plot with different amplitudes.

    """
    def __init__(self, base: PlotItem):
        super().__init__(enableMenu=False)
        self._base = base
        self.legend = base.legend
        self.setXLink(self._base)
        self.buttonsHidden = True
        self.hideAxis('left')
        self.hideAxis('bottom')
        self.setZValue(-100)

        base.showAxis('right')
        base.getAxis('right').setGrid(False)
        base.getAxis('right').linkToView(self.getViewBox())
        base.layout.addItem(self, 2, 1)


class GridPlotWidget(GraphicsView):
    """
    Base plotting class used to create a group of 1 or more :class:`PlotItem`
    in a layout (rows/columns).
    This class is a subclass of :class:`QWidget` and can be directly added to a
    QtWidget based application.

    This is essentially a wrapper around PyQtGraph's GraphicsLayout, which
    handles the complexities of creating/laying-out plots in the view. This
    class aims to simplify the API for our use cases, and add functionality for
    easily plotting pandas Series.

    Parameters
    ----------
    rows : int, Optional
        Rows of plots to generate (stacked from top to bottom), default is 1
    background : Optional
        Background color for the widget and nested plots. Can be any value
        accepted by :func:`mkBrush` or :func:`mkColor` e.g. QColor, hex string,
        RGB(A) tuple
    grid : bool
        If True displays gridlines on the plot surface
    sharex : bool
        If True links all x-axis values to the first plot
    multiy : bool
        If True all plots will have a sister plot with its own y-axis and scale
        enabling the plotting of 2 (or more) Series with differing scales on a
        single plot surface.
    parent

    See Also
    --------
    :func:`pyqtgraph.functions.mkPen` for customizing plot-line pens (creates a QgGui.QPen)
    :func:`pyqtgraph.functions.mkColor` for color options in the plot (creates a QtGui.QColor)

    """

    def __init__(self, rows=1, cols=1, background='w', grid=True, sharex=False,
                 multiy=False, parent=None):
        super().__init__(background=background, parent=parent)
        self.gl = GraphicsLayout(parent=parent)
        self.setCentralItem(self.gl)

        self.rows = rows
        self.cols = cols

        self._pens = cycle([{'color': v, 'width': 2} for v in LINE_COLORS])
        self._series = {}  # type: Dict[pd.Series: Tuple[str, int, int]]
        self._items = {}  # type: Dict[PlotDataItem: Tuple[str, int, int]]
        self._rightaxis = {}

        col = 0
        for row in range(self.rows):
            axis_items = {'bottom': PolyAxis(orientation='bottom')}
            plot: PlotItem = self.gl.addPlot(row=row, col=col,
                                             backround=background,
                                             axisItems=axis_items)
            plot.clear()
            plot.addLegend(offset=(15, 15))
            plot.showGrid(x=grid, y=grid)
            plot.setYRange(-1, 1)  # Prevents overflow when labels are added
            if row > 0 and sharex:
                plot.setXLink(self.get_plot(0, 0))
            if multiy:
                p2 = LinkedPlotItem(plot)
                self._rightaxis[(row, col)] = p2

        self.__signal_proxies = []

    def get_plot(self, row: int, col: int = 0, axis: str = 'left') -> PlotItem:
        if axis == 'right':
            return self._rightaxis[(row, col)]
        else:
            return self.gl.getItem(row, col)

    @property
    def plots(self) -> Generator[PlotItem, None, None]:
        for i in range(self.rows):
            yield self.get_plot(i, 0)

    def add_series(self, series: pd.Series, row: int, col: int = 0,
                   axis: str = 'left'):
        """Add a pandas :class:`pandas.Series` to the plot at the specified
        row/column

        Parameters
        ----------
        series : :class:`~pandas.Series`
            The Pandas Series to add; series.index and series.values are taken
            to be the x and y axis respectively
        row : int
        col : int
        axis : str
            'left' or 'right' - specifies which y-scale the series should be
            plotted on. Only has effect if self.multiy is True.

        Returns
        -------

        """
        key = self.make_index(series.name, row, col, axis)
        if self.get_series(*key) is not None:
            return

        self._series[key] = series
        if axis == 'right':
            plot = self._rightaxis.get((row, col), self.get_plot(row, col))
        else:
            plot = self.get_plot(row, col)
        xvals = pd.to_numeric(series.index, errors='coerce')
        yvals = pd.to_numeric(series.values, errors='coerce')
        item = plot.plot(x=xvals, y=yvals, name=series.name, pen=next(self._pens))
        self._items[key] = item
        return item

    def get_series(self, name: str, row, col=0, axis='left') -> Union[pd.Series, None]:
        return self._series.get((name, row, col, axis), None)

    def remove_series(self, name: str, row: int, col: int = 0) -> None:
        plot = self.get_plot(row, col)
        key = self.make_index(name, row, col)
        plot.removeItem(self._items[key])
        plot.legend.removeItem(name)
        del self._series[key]
        del self._items[key]

    def clear(self):
        for i in range(self.rows):
            for j in range(self.cols):
                plot = self.get_plot(i, j)
                plot.clear()
        self._items = {}
        self._series = {}

    def remove_plotitem(self, item: PlotDataItem) -> None:
        """Alternative method of removing a line by its :class:`PlotDataItem`
        reference, as opposed to using remove_series to remove a named series
        from a specific plot at row/col index.

        Parameters
        ----------
        item : :class:`PlotDataItem`
            The PlotDataItem reference to be removed from whichever plot it
            resides

        """
        for plot, index in self.gl.items.items():
            if isinstance(plot, PlotItem):  # pragma: no branch
                if item in plot.dataItems:
                    name = item.name()
                    plot.removeItem(item)
                    plot.legend.removeItem(name)

                    del self._series[self.make_index(name, *index[0])]

    def find_series(self, name: str) -> List[Tuple[str, int, int]]:
        indexes = []
        for index, series in self._series.items():
            if series.name == name:  # pragma: no branch
                indexes.append(index)

        return indexes

    def set_xaxis_formatter(self, formatter: str, row: int, col: int = 0):
        """Allow setting of the X-Axis tick formatter to display DateTime or
        scalar values.
        This is an explicit call, as opposed to letting the AxisItem infer the
        axis type due to the possibility of plotting two series with different
        indexes. This may be revised in future.

        Parameters
        ----------
        formatter : str
            'datetime' will set the bottom AxisItem to display datetime values
            Any other value will set the AxisItem to its default scalar display
        row : int
            Plot row index
        col : int
            Plot column index

        """
        plot = self.get_plot(row, col)
        axis: PolyAxis = plot.getAxis('bottom')
        if formatter.lower() == 'datetime':
            axis.timeaxis = True
        else:
            axis.timeaxis = False

    def get_xlim(self, row: int, col: int = 0):
        return self.get_plot(row, col).vb.viewRange()[0]

    def set_xlink(self, linked: bool = True, autorange: bool = False):
        """Enable or disable linking of x-axis' between all plots in the grid.

        Parameters
        ----------
        linked : bool, Optional
            If True sets all plots to link x-axis scales with plot 0, 0
            If False, un-links all plot x-axis'
        autorange : bool, Optional
            If True automatically re-scale the view box after linking/unlinking

        """
        base = self.get_plot(0, 0) if linked else None
        for i in range(1, self.rows):
            plot = self.get_plot(i, 0)
            plot.setXLink(base)
            if autorange:
                plot.autoRange()

    def add_onclick_handler(self, slot, ratelimit: int = 60):  # pragma: no cover
        """Creates a SignalProxy to forward Mouse Clicked events on the
        GraphicsLayout scene to the provided slot.

        Parameters
        ----------
        slot : pyqtSlot(MouseClickEvent)
            pyqtSlot accepting a :class:`MouseClickEvent`
        ratelimit : int, optional
            Limit the SignalProxy to an emission rate of `ratelimit` signals/sec

        """
        sp = SignalProxy(self.gl.scene().sigMouseClicked, rateLimit=ratelimit,
                         slot=slot)
        self.__signal_proxies.append(sp)
        return sp

    @staticmethod
    def make_index(name: str, row: int, col: int = 0, axis: str = 'left'):
        if axis not in ('left', 'right'):
            axis = 'left'
        if name is None or name is '':
            raise ValueError("Cannot create plot index from empty name.")
        return name.lower(), row, col, axis


class PyQtGridPlotWidget(GraphicsView):  # pragma: no cover
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

