# -*- coding: utf-8 -*-
from enum import Enum, auto
from itertools import cycle
from typing import List, Union, Tuple, Generator, Dict

import pandas as pd
from pyqtgraph.widgets.GraphicsView import GraphicsView
from pyqtgraph.graphicsItems.GraphicsLayout import GraphicsLayout
from pyqtgraph.graphicsItems.PlotItem import PlotItem
from pyqtgraph import SignalProxy, PlotDataItem

from .helpers import PolyAxis


__all__ = ['GridPlotWidget', 'Axis', 'AxisFormatter']


class AxisFormatter(Enum):
    DATETIME = auto()
    SCALAR = auto()


class Axis(Enum):
    LEFT = 'left'
    RIGHT = 'right'


MaybeSeries = Union[pd.Series, None]
PlotIndex = Tuple[str, int, int, Axis]
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
                 multiy=False, timeaxis=False, parent=None):
        super().__init__(background=background, parent=parent)
        self.gl = GraphicsLayout(parent=parent)
        self.setCentralItem(self.gl)

        self.rows = rows
        self.cols = cols

        # Note: increasing pen width can drastically reduce performance
        self._pens = cycle([{'color': v, 'width': 1} for v in LINE_COLORS])
        self._series = {}  # type: Dict[pd.Series: Tuple[str, int, int]]
        self._items = {}  # type: Dict[PlotDataItem: Tuple[str, int, int]]
        self._rightaxis = {}

        # TODO: use plot.setLimits to restrict zoom-out level (prevent OverflowError)
        col = 0
        for row in range(self.rows):
            axis_items = {'bottom': PolyAxis(orientation='bottom',
                                             timeaxis=timeaxis)}
            plot: PlotItem = self.gl.addPlot(row=row, col=col,
                                             backround=background,
                                             axisItems=axis_items)
            plot.clear()
            plot.addLegend(offset=(15, 15))
            plot.showGrid(x=grid, y=grid)
            plot.setYRange(-1, 1)  # Prevents overflow when labels are added
            plot.setLimits(maxYRange=1e17, maxXRange=1e17)

            if row > 0 and sharex:
                plot.setXLink(self.get_plot(0, 0))
            if multiy:
                p2 = LinkedPlotItem(plot)
                p2.setLimits(maxYRange=1e17, maxXRange=1e17)
                self._rightaxis[(row, col)] = p2

        self.__signal_proxies = []

    def get_plot(self, row: int, col: int = 0, axis: Axis = Axis.LEFT) -> PlotItem:
        if axis is Axis.RIGHT:
            return self._rightaxis[(row, col)]
        else:
            return self.gl.getItem(row, col)

    @property
    def plots(self) -> Generator[PlotItem, None, None]:
        for i in range(self.rows):
            yield self.get_plot(i, 0)

    def add_series(self, series: pd.Series, row: int, col: int = 0,
                   axis: Axis = Axis.LEFT, autorange: bool = True) -> PlotItem:
        """Add a pandas :class:`pandas.Series` to the plot at the specified
        row/column

        Parameters
        ----------
        series : :class:`~pandas.Series`
            The Pandas Series to add; series.index and series.values are taken
            to be the x and y axis respectively
        row : int
        col : int, optional
        axis : str, optional
            'left' or 'right' - specifies which y-scale the series should be
            plotted on. Only has effect if self.multiy is True.
        autorange : bool, optional

        Returns
        -------
        PlotItem

        """
        key = self.make_index(series.name, row, col, axis)
        if self.get_series(*key) is not None:
            return self._items[key]

        self._series[key] = series
        if axis is Axis.RIGHT:
            plot = self._rightaxis.get((row, col), self.get_plot(row, col))
        else:
            plot = self.get_plot(row, col)
        xvals = pd.to_numeric(series.index, errors='coerce')
        yvals = pd.to_numeric(series.values, errors='coerce')
        item = plot.plot(x=xvals, y=yvals, name=series.name, pen=next(self._pens))
        self._items[key] = item
        if autorange:
            self.autorange_plot(row, col)
        return item

    def get_series(self, name: str, row, col=0, axis: Axis = Axis.LEFT) -> MaybeSeries:
        idx = self.make_index(name, row, col, axis)
        return self._series.get(idx, None)

    def remove_series(self, name: str, row: int, col: int = 0,
                      axis: Axis = Axis.LEFT, autoscale: bool = True) -> None:
        plot = self.get_plot(row, col, axis)
        key = self.make_index(name, row, col, axis)
        plot.removeItem(self._items[key])
        plot.legend.removeItem(name)
        del self._series[key]
        del self._items[key]
        if autoscale:
            self.autorange_plot(row, col)

    def clear(self):
        for i in range(self.rows):
            for j in range(self.cols):
                plot = self.get_plot(i, j)
                for curve in plot.curves[:]:
                    name = curve.name()
                    plot.removeItem(curve)
                    plot.legend.removeItem(name)
                if self._rightaxis:
                    plot_r = self.get_plot(i, j, axis=Axis.RIGHT)
                    for curve in plot_r.curves[:]:
                        name = curve.name()
                        plot_r.removeItem(curve)
                        plot.legend.removeItem(name)  # Legend is only on left
                        del curve
        del self._items
        del self._series
        self._items = {}
        self._series = {}

    def autorange_plot(self, row: int, col: int = 0):
        plot_l = self.get_plot(row, col, axis=Axis.LEFT)
        plot_l.autoRange(items=plot_l.curves)
        if self._rightaxis:
            plot_r = self.get_plot(row, col, axis=Axis.RIGHT)
            plot_r.autoRange(items=plot_r.curves)

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

    def find_series(self, name: str) -> List[PlotIndex]:
        """Find and return a list of all indexes where a series with
        Series.name == name

        Parameters
        ----------
        name : str
            Name of the :class:`pandas.Series` to find indexes of

        Returns
        -------
        List
            List of Series indexes, see :func:`make_index`

        """
        indexes = []
        for index, series in self._series.items():
            if series.name == name:  # pragma: no branch
                indexes.append(index)

        return indexes

    def set_xaxis_formatter(self, formatter: AxisFormatter, row: int, col: int = 0):
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
        if formatter is AxisFormatter.DATETIME:
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
    def make_index(name: str, row: int, col: int = 0, axis: Axis = Axis.LEFT) -> PlotIndex:
        if axis not in Axis:
            axis = Axis.LEFT
        if name is None or name is '':
            raise ValueError("Cannot create plot index from empty name.")
        return name.lower(), row, col, axis

