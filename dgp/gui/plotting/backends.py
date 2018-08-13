# -*- coding: utf-8 -*-
from enum import Enum, auto
from itertools import cycle
from typing import List, Union, Tuple, Generator, Dict
from weakref import WeakValueDictionary

import pandas as pd
from PyQt5.QtWidgets import QMenu, QWidgetAction, QWidget, QAction
from pyqtgraph.widgets.GraphicsView import GraphicsView
from pyqtgraph.graphicsItems.GraphicsLayout import GraphicsLayout
from pyqtgraph.graphicsItems.PlotItem import PlotItem
from pyqtgraph import SignalProxy, PlotDataItem

from dgp.gui.ui.plot_options_widget import Ui_PlotOptions
from .helpers import PolyAxis

__all__ = ['GridPlotWidget', 'Axis', 'AxisFormatter']


class AxisFormatter(Enum):
    DATETIME = auto()
    SCALAR = auto()


class Axis(Enum):
    LEFT = 'left'
    RIGHT = 'right'


LINE_COLORS = {'#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
               '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'}


# type aliases
MaybePlot = Union['DgpPlotItem', None]
MaybeSeries = Union[pd.Series, None]
PlotIndex = Tuple[str, int, int, Axis]


class _CustomPlotControl(QWidget, Ui_PlotOptions):
    """QWidget used by DgpPlotItem to provide a custom plot-controls menu."""
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self._action = QWidgetAction(parent)
        self._action.setDefaultWidget(self)
        self.qpbReset.clicked.connect(self.reset_controls)

    def reset_controls(self):
        """Reset all controls to a default state/value"""
        self.alphaGroup.setChecked(True)
        self.alphaSlider.setValue(1000)
        self.gridAlphaSlider.setValue(128)
        self.xGridCheck.setChecked(True)
        self.yGridCheck.setChecked(True)
        self.yGridCheckRight.setChecked(False)
        self.averageCheck.setChecked(False)
        self.downsampleCheck.setChecked(False)
        self.downsampleSpin.setValue(1)

    @property
    def action(self) -> QWidgetAction:
        return self._action


class LinkedPlotItem(PlotItem):
    """LinkedPlotItem creates a twin plot linked to the right y-axis of the base

    This class is used by DgpPlotItem to enable plots which have a second
    y-axis scale in order to display two (or potentially more) Series on the
    same plot with different magnitudes.

    Notes
    -----
    This class is a simple wrapper around a base pyqtgraph PlotItem, it sets
    some sensible default parameters, and configures itself to link its x-axis
    to the specified 'base' PlotItem, and finally inserts itself into the layout
    container of the parent plot.
    Also note that the linked plot does not use its own independent legend,
    it links its legend attribute to the base plot's legend (so that legend
    add/remove actions can be performed without validating the specific plot
    reference).

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
        self.setLimits(maxYRange=1e17, maxXRange=1e17)

        base.showAxis('right')
        base.getAxis('right').setGrid(False)
        base.getAxis('right').linkToView(self.getViewBox())
        base.layout.addItem(self, 2, 1)


class DgpPlotItem(PlotItem):
    """Custom PlotItem derived from pyqtgraph's :class:`PlotItem`

    The primary focus of this custom PlotItem is to override the default
    'Plot Options' sub-menu provided by PlotItem for context-menu (right-click)
    events on the plot surface.
    Secondarily this class provides a simple way to create/enable a secondary
    y-axis, for plotting multiple data curves of differing magnitudes.

    Many of the menu actions defined by the original PlotItem class do not work
    correctly (or generate RuntimeErrors) when dealing with typical DataFrames
    in our context. The original menu is also heavily nested, and provides many
    functions which are currently unnecessary for our use-case.

    The custom Plot Options menu provided by this class is a single frame
    pop-out context menu, providing the functions/actions described in the notes
    below.

    Parameters
    ----------
    multiy : bool, optional
        If True the plot item will be created with multiple y-axis scales.
        Curves can be plotted to the second (right axis) plot using the 'right'
        property
    kwargs
        See valid parameters for :class:`PlotItem`

    Notes
    -----
    Custom menu functionality provided:
    - Plot curve alpha (transparency) setting
    - Grid line visibility (on/off/transparency)
    - Average curve (on/off)
    - Downsampling/decimation - selectable data-decimation by step (2 to 10)

    """
    ctrl_overrides = ('alphaSlider', 'alphaGroup', 'gridAlphaSlider',
                      'xGridCheck', 'yGridCheck', 'downsampleCheck',
                      'downsampleSpin')

    def __init__(self, multiy: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.setLimits(maxYRange=1e17, maxXRange=1e17)
        self.setYRange(-1, 1)
        self.addLegend(offset=(15, 15))

        self.customControl = _CustomPlotControl()
        self.ctrlMenu = QMenu("Plot Options")
        self.ctrlMenu.addAction(self.customControl.action)

        # Ensure default state in original ui ctrl
        self.ctrl.alphaGroup.setChecked(True)
        self.ctrl.autoAlphaCheck.setChecked(False)

        # Set signal connections for custom controls
        self.customControl.alphaGroup.toggled.connect(self.updateAlpha)
        self.customControl.alphaSlider.valueChanged.connect(self.updateAlpha)
        self.customControl.gridAlphaSlider.valueChanged.connect(self.updateGrid)
        self.customControl.xGridCheck.toggled.connect(self.updateGrid)
        self.customControl.yGridCheck.toggled.connect(self.updateGrid)
        self.customControl.yGridCheckRight.toggled.connect(self.updateGrid)
        self.customControl.averageCheck.toggled.connect(self.ctrl.averageGroup.setChecked)
        self.customControl.downsampleCheck.toggled.connect(self.updateDownsampling)
        self.customControl.downsampleSpin.valueChanged.connect(self.updateDownsampling)

        # Patch original controls whose state/value is used in various updates
        # e.g. PlotItem.updateGrid checks the checked state of x/yGridCheck
        # This is done so we don't have to override every base update function
        for attr in self.ctrl_overrides:
            setattr(self.ctrl, attr, getattr(self.customControl, attr))

        self.updateGrid()

        self.clearAction = QAction("Clear Plot", self)
        self.clearAction.triggered.connect(self.clearPlots)

        # Connect the 'View All' action so it autoRanges both (left/right) plots
        self.vb.menu.viewAll.triggered.disconnect()
        self.vb.menu.viewAll.triggered.connect(self.autoRange)

        # Configure right-y plot (sharing x-axis)
        self._right = LinkedPlotItem(self) if multiy else None

    @property
    def left(self) -> 'DgpPlotItem':
        return self

    @property
    def right(self) -> MaybePlot:
        """Return the sibling plot linked to the right y-axis (if it exists)"""
        return self._right

    def clearPlots(self):
        """Override PlotItem::clearPlots

        Clear all curves from left and right plots, as well as removing any
        legend entries.
        """
        for c in self.curves[:]:
            self.legend.removeItem(c.name())
            self.removeItem(c)
        self.avgCurves = {}

        if self.right is not None:
            for c in self.right.curves[:]:
                self.legend.removeItem(c.name())
                self.right.removeItem(c)

    def autoRange(self, *args, **kwargs):
        self.vb.autoRange(items=self.curves)
        if self.right is not None:
            self.right.vb.autoRange(items=self.right.curves)

    def updateAlpha(self, *args):
        super().updateAlpha(*args)
        if self.right is not None:
            alpha, auto_ = self.alphaState()
            for c in self.right.curves:
                c.setAlpha(alpha**2, auto_)

    def updateDownsampling(self):
        """Override PlotItem::updateDownsampling

        Override the base implementation in order to effect updates on the right
        plot (if it is enabled).
        """
        super().updateDownsampling()
        if self.right is not None:
            ds, auto_, method = self.downsampleMode()
            for c in self.right.curves:
                c.setDownsampling(ds, auto_, method)

    def downsampleMode(self):
        """Override PlotItem::downsampleMode

        Called by updateDownsampling to get control state. Our custom
        implementation does not allow for all of the options that the original
        does.

        """
        if self.ctrl.downsampleCheck.isChecked():
            ds = self.ctrl.downsampleSpin.value()
        else:
            ds = 1
        return ds, False, 'subsample'

    def updateGrid(self, *args):
        alpha = self.customControl.gridAlphaSlider.value()
        x = alpha if self.customControl.xGridCheck.isChecked() else False
        y = alpha if self.customControl.yGridCheck.isChecked() else False
        yr = alpha if self.customControl.yGridCheckRight.isChecked() else False

        self.getAxis('bottom').setGrid(x)
        self.getAxis('left').setGrid(y)
        self.getAxis('right').setGrid(yr)

    def getContextMenus(self, event):
        if self.menuEnabled():
            return [self.ctrlMenu, self.clearAction]
        else:
            return None


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

    Notes
    -----
    The GridPlotWidget explicitly disables the :class:`pyqtgraph.GraphicsScene`
    'Export' context menu action, as the export dialog is not fully suitable for
    our purposes. Similar functionality may be added to the application later,
    but not via the plotting interface.

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

        # Remove the 'Export' option from the scene context menu
        self.sceneObj.contextMenu = []

        self.rows = rows
        self.cols = cols

        # Note: increasing pen width can drastically reduce performance
        self._pens = cycle([{'color': v, 'width': 1} for v in LINE_COLORS])

        # Maintain weak references to Series/PlotDataItems for lookups
        self._series: Dict[PlotIndex: pd.Series] = WeakValueDictionary()
        self._items: Dict[PlotIndex: PlotDataItem] = WeakValueDictionary()

        col = 0
        for row in range(self.rows):
            axis_items = {'bottom': PolyAxis(orientation='bottom',
                                             timeaxis=timeaxis)}
            plot = DgpPlotItem(background=background, axisItems=axis_items,
                               multiy=multiy)
            self.gl.addItem(plot, row=row, col=col)
            plot.clear()
            plot.showGrid(x=grid, y=grid)

            if row > 0 and sharex:
                plot.setXLink(self.get_plot(0, 0))

        self.__signal_proxies = []

    @property
    def plots(self) -> Generator[DgpPlotItem, None, None]:
        for i in range(self.rows):
            yield self.get_plot(i, 0)

    @property
    def pen(self):
        return next(self._pens)

    def autorange(self):
        """Call auto-range on all plots in the GridPlotWidget"""
        for plot in self.plots:
            plot.autoRange()

    def get_plot(self, row: int, col: int = 0, axis: Axis = Axis.LEFT) -> MaybePlot:
        plot: DgpPlotItem = self.gl.getItem(row, col)
        if axis is Axis.RIGHT:
            return plot.right
        else:
            return plot

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

        Raises
        ------
        :exc:`AttributeError`
            If the provided axis is invalid for the plot, i.e. axis=Axis.RIGHT
            but multiy is not enabled.

        """
        key = self.make_index(series.name, row, col, axis)
        if self._items.get(key, None) is not None:
            return self._items[key]

        self._series[key] = series
        plot = self.get_plot(row, col, axis)
        xvals = pd.to_numeric(series.index, errors='coerce')
        yvals = pd.to_numeric(series.values, errors='coerce')
        item = plot.plot(x=xvals, y=yvals, name=series.name, pen=self.pen)
        self._items[key] = item
        if autorange:
            plot.autoRange()
        return item

    def get_series(self, name: str, row, col=0, axis: Axis = Axis.LEFT) -> MaybeSeries:
        idx = self.make_index(name, row, col, axis)
        return self._series.get(idx, None)

    def remove_series(self, name: str, row: int, col: int = 0,
                      axis: Axis = Axis.LEFT, autorange: bool = True) -> None:
        """Remove a named series from the plot at the specified row/col/axis

        Parameters
        ----------
        name : str
        row : int
        col : int, optional
        axis : Axis, optional
        autorange : bool, optional
            Readjust plot x/y view limits after removing the series

        """
        plot = self.get_plot(row, col, axis)
        key = self.make_index(name, row, col, axis)
        plot.removeItem(self._items[key])
        plot.legend.removeItem(name)
        if autorange:
            plot.autoRange()

    def clear(self):
        """Clear all plot curves from all plots"""
        for i in range(self.rows):
            for j in range(self.cols):
                plot = self.get_plot(i, j)
                for curve in plot.curves[:]:
                    name = curve.name()
                    plot.removeItem(curve)
                    plot.legend.removeItem(name)
                if plot.right:
                    plot_r = plot.right
                    for curve in plot_r.curves[:]:
                        plot_r.legend.removeItem(curve.name())
                        plot_r.removeItem(curve)

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
                    plot.legend.removeItem(item.name())
                    plot.removeItem(item)

    def find_series(self, name: str) -> List[PlotIndex]:
        """Find and return a list of all plot indexes where a series with
        'name' is plotted

        Parameters
        ----------
        name : str
            Name of the :class:`pandas.Series` to find indexes of

        Returns
        -------
        List of PlotIndex
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
        axis.timeaxis = formatter is AxisFormatter.DATETIME

    def get_xlim(self, row: int, col: int = 0) -> Tuple[float, float]:
        """Get the x-limits (span) for the plot at row/col

        Returns
        -------
        tuple of float, float
            Tuple of minimum/maximum x-values (xmin, xmax)

        """
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
        """Generate an index referring to a specific plot curve

        Plot curves (items) can be uniquely identified within the GridPlotWidget
        by their name, and the specific plot which they reside on (row/col/axis)
        A plot item can only be plotted once on a given plot, so the index is
        guaranteed to be unique for the specific named item.

        Raises
        ------
        :exc:`ValueError`
            If supplied name is invalid (None or empty string: '')

        """
        if axis not in Axis:
            axis = Axis.LEFT
        if name is None or name is '':
            raise ValueError("Cannot create plot index from empty name.")
        return name.lower(), row, col, axis
