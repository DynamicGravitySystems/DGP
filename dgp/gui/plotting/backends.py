# coding: utf-8

from abc import ABCMeta, abstractmethod
from functools import partial, partialmethod
from itertools import cycle
from typing import Union

from PyQt5.QtCore import pyqtSignal
import PyQt5.QtWidgets as QtWidgets
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent, PickEvent
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg)
from matplotlib.dates import DateFormatter
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.ticker import AutoLocator
from pyqtgraph.widgets.GraphicsView import GraphicsView
from pyqtgraph.graphicsItems.GraphicsLayout import GraphicsLayout
from pyqtgraph.graphicsItems.AxisItem import AxisItem
from pyqtgraph.graphicsItems.PlotDataItem import PlotDataItem
from pyqtgraph.graphicsItems.InfiniteLine import InfiniteLine
from pyqtgraph.graphicsItems.ViewBox import ViewBox
from pyqtgraph.graphicsItems.LinearRegionItem import LinearRegionItem
from pyqtgraph.widgets.PlotWidget import PlotWidget, PlotItem
from pyqtgraph import SignalProxy

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

It remains to be seen if the Interface/ABC SeriesPlotter and its descendent 
classes PlotWidgetWrapper and MPLAxesWrapper are necessary - the intent of 
these classes was to wrap a PlotItem or Axes and provide a unified standard 
interface for plotting. However, the Stacked*Widget classes might nicely 
encapsulate what was intended there.
"""
__all__ = ['PYQTGRAPH', 'MATPLOTLIB', 'BasePlot', 'StackedMPLWidget',
           'PyQtGridPlotWidget',
           'SeriesPlotter']

PYQTGRAPH = 'pqg'
MATPLOTLIB = 'mpl'


class BasePlot:
    """Creates a new Plot Widget with the specified backend (Matplotlib,
    or PyQtGraph), or returns a StackedMPLWidget if none specified."""
    def __new__(cls, *args, **kwargs):
        backend = kwargs.get('backend', '')
        if backend.lower() == PYQTGRAPH:
            kwargs.pop('backend')
            # print("Initializing StackedPGWidget with KWArgs: ", kwargs)
            return PyQtGridPlotWidget(*args, **kwargs)
        else:
            return StackedMPLWidget(*args, **kwargs)


class DateAxis(AxisItem):
    minute = pd.Timedelta(minutes=1).value
    hour = pd.Timedelta(hours=1).value
    day = pd.Timedelta(days=2).value

    def tickStrings(self, values, scale, spacing):
        """

        Parameters
        ----------
        values : List
            List of values to return strings for
        scale : Scalar
            Used for SI notation prefixes
        spacing : Scalar
            Spacing between values/ticks

        Returns
        -------
        List of strings used to label the plot at the given values

        Notes
        -----
        This function may be called multiple times for the same plot,
        where multiple tick-levels are defined i.e. Major/Minor/Sub-Minor ticks.
        The range of the values may also differ between invocations depending on
        the positioning of the chart. And the spacing will be different
        dependent on how the ticks were placed by the tickSpacing() method.

        """
        if not values:
            rng = 0
        else:
            rng = max(values) - min(values)

        labels = []
        # TODO: Maybe add special tick format for first tick
        if rng < self.minute:
            fmt = '%H:%M:%S'

        elif rng < self.hour:
            fmt = '%H:%M:%S'
        elif rng < self.day:
            fmt = '%H:%M'
        else:
            if spacing > self.day:
                fmt = '%y:%m%d'
            elif spacing >= self.hour:
                fmt = '%H'
            else:
                fmt = ''

        for x in values:
            try:
                labels.append(pd.to_datetime(x).strftime(fmt))
            except ValueError:  # Windows can't handle dates before 1970
                labels.append('')
            except OSError:
                pass
        return labels

    def tickSpacing(self, minVal, maxVal, size):
        """
        The return value must be a list of tuples, one for each set of ticks::

            [
                (major tick spacing, offset),
                (minor tick spacing, offset),
                (sub-minor tick spacing, offset),
                ...
            ]

        """
        rng = pd.Timedelta(maxVal - minVal).value
        # offset = pd.Timedelta(seconds=36).value
        offset = 0
        if rng < pd.Timedelta(minutes=5).value:
            mjrspace = pd.Timedelta(seconds=15).value
            mnrspace = pd.Timedelta(seconds=5).value
        elif rng < self.hour:
            mjrspace = pd.Timedelta(minutes=5).value
            mnrspace = pd.Timedelta(minutes=1).value
        elif rng < self.day:
            mjrspace = pd.Timedelta(hours=1).value
            mnrspace = pd.Timedelta(minutes=5).value
        else:
            return [(pd.Timedelta(hours=12).value, offset)]

        spacing = [
            (mjrspace, offset),  # Major
            (mnrspace, offset)   # Minor
        ]
        return spacing


class StackedMPLWidget(FigureCanvasQTAgg):
    def __init__(self, rows=1, sharex=True, width=8, height=4, dpi=100,
                 parent=None):
        super().__init__(Figure(figsize=(width, height), dpi=dpi,
                                tight_layout=True))
        self.setParent(parent)
        super().setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                              QtWidgets.QSizePolicy.Expanding)
        super().updateGeometry()

        self.figure.canvas.mpl_connect('pick_event', self.onpick)
        self.figure.canvas.mpl_connect('button_press_event', self.onclick)
        self.figure.canvas.mpl_connect('button_release_event', self.onrelease)
        self.figure.canvas.mpl_connect('motion_notify_event', self.onmotion)

        self._plots = []
        self.plots = []

        spec = GridSpec(nrows=rows, ncols=1)
        for row in range(rows):
            if row >= 1 and sharex:
                plot = self.figure.add_subplot(spec[row], sharex=self._plots[0])
            else:
                plot = self.figure.add_subplot(spec[row])

            if row == rows - 1:
                # Add x-axis ticks on last plot only
                plot.xaxis.set_major_locator(AutoLocator())
                # TODO: Dynamically apply this
                plot.xaxis.set_major_formatter(DateFormatter("%H:%M:%S"))
            self._plots.append(plot)
            self.plots.append(MPLAxesWrapper(plot, self.figure.canvas))

    def __len__(self):
        return len(self._plots)

    def get_plot(self, row) -> 'SeriesPlotter':
        return self.plots[row]

    def onclick(self, event: MouseEvent):
        pass

    def onrelease(self, event: MouseEvent):
        pass

    def onmotion(self, event: MouseEvent):
        pass

    def onpick(self, event: PickEvent):
        pass


class PyQtGridPlotWidget(GraphicsView):
    def __init__(self, rows=1, cols=1, background='w', grid=True,
                 sharex=True, sharey=False, tickFormatter='date', parent=None):
        super().__init__(parent=parent, background=background)
        self._gl = GraphicsLayout(parent=parent)
        self.setCentralItem(self._gl)
        self._plots = []
        self._wrapped = []
        # Store ref to signal proxies so they are not GC'd
        self._sigproxies = []

        for row in range(rows):
            for col in range(cols):
                date_fmtr = None
                if tickFormatter == 'date':
                    date_fmtr = DateAxis(orientation='bottom')
                plot = self._gl.addPlot(row=row, col=col, background=background,
                                        axisItems={'bottom': date_fmtr})
                plot.getAxis('left').setWidth(40)

                if len(self._plots) > 0:
                    if sharex:
                        plot.setXLink(self._plots[0])
                    if sharey:
                        plot.setYLink(self._plots[0])

                plot.showGrid(x=grid, y=grid)
                plot.addLegend(offset=(-15, 15))
                self._plots.append(plot)
                self._wrapped.append(PlotWidgetWrapper(plot))

    def __len__(self):
        return len(self._plots)

    def add_series(self, series, idx=0, *args, **kwargs):
        return self._wrapped[idx].add_series(series, *args, **kwargs)

    def remove_series(self, series):
        for plot in self._wrapped:
            plot.remove_series(id(series))

    def add_onclick_handler(self, slot, rateLimit=60):
        sp = SignalProxy(self._gl.scene().sigMouseClicked, rateLimit=rateLimit,
                         slot=slot)
        self._sigproxies.append(sp)
        return sp

    @property
    def plots(self):
        return self._wrapped

    def get_plot(self, row):
        return self._plots[row]


class SeriesPlotter(metaclass=ABCMeta):
    """
    Abstract Base Class used to define an interface for different plotter
    wrappers.

    """
    sigItemPlotted = pyqtSignal()

    colors = ['r', 'g', 'b', 'g']
    colorcycle = cycle([{'color': v} for v in colors])

    def __getattr__(self, item):
        """Passes attribute calls to underlying plotter object if no override
        in SeriesPlotter implementation."""
        if hasattr(self.plotter, item):
            attr = getattr(self.plotter, item)
            return attr
        raise AttributeError(item)

    @property
    @abstractmethod
    def plotter(self) -> Union[Axes, PlotWidget]:
        """This property should return the underlying plot object, either a
        Matplotlib Axes or a PyQtgraph PlotWidget"""
        pass

    @property
    @abstractmethod
    def items(self):
        """This property should return a list or a generator which yields the
        items plotted on the plot."""
        pass

    @abstractmethod
    def plot(self, *args, **kwargs):
        pass

    @abstractmethod
    def add_series(self, series, *args, **kwargs):
        pass

    @abstractmethod
    def remove_series(self, series):
        pass

    @abstractmethod
    def draw(self) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        """This method should clear all items from the Plotter"""
        pass

    @abstractmethod
    def get_xlim(self):
        pass

    @abstractmethod
    def get_ylim(self):
        pass


class PlotWidgetWrapper(SeriesPlotter):
    def __init__(self, plot: PlotItem):

        self._plot = plot
        self._lines = {}  # id(Series): line
        self._data = {}   # id(Series): series

    def __len__(self):
        return len(self._lines)

    @property
    def plotter(self) -> PlotWidget:
        return self._plot

    @property
    def _plotitem(self) -> PlotItem:
        # return self._plot.plotItem
        return self._plot

    @property
    def items(self):
        for item in self._lines.values():
            yield item

    def plot(self, x, y, *args, **kwargs):
        if isinstance(x, pd.Series):

            pass
        else:
            self._plot.plot(x, y, *args, **kwargs)

        pass

    def add_series(self, series: pd.Series, fmter='date', *args, **kwargs):
        """Take in a pandas Series, add it to the plot and retain a
        reference.

        Parameters
        ----------
        series : pd.Series
        fmter : str
            'date' or 'scalar'
            Set the plot to use a date formatter or scalar formatter on the
            x-axis
        """
        sid = id(series)
        if sid in self._lines:
            print("Series already plotted")
            return
        xvals = pd.to_numeric(series.index, errors='coerce')
        yvals = pd.to_numeric(series.values, errors='coerce')

        line = self._plot.plot(x=xvals, y=yvals,
                               name=series.name,
                               pen=next(self.colorcycle))  # type: PlotDataItem
        self._lines[sid] = line
        # self.sigItemPlotted.emit()
        return line

    def remove_series(self, sid):
        # sid = id(series)
        if sid not in self._lines:
            return
        self._plotitem.legend.removeItem(self._lines[sid].name())
        self._plot.removeItem(self._lines[sid])
        del self._lines[sid]

    def draw(self):
        """Draw is uncecesarry for Pyqtgraph plots"""
        pass

    def clear(self):
        pass

    def get_ylim(self):
        return self._plotitem.vb.viewRange()[1]

    def get_xlim(self):
        return self._plotitem.vb.viewRange()[0]


class MPLAxesWrapper(SeriesPlotter):

    def __init__(self, plot, canvas):
        assert isinstance(plot, Axes)
        self._plot = plot
        self._lines = {}  # id(Series): Line2D
        self._canvas = canvas  # type: FigureCanvas

    @property
    def plotter(self) -> Axes:
        return self._plot

    @property
    def items(self):
        for item in self._lines.values():
            yield item

    def plot(self, *args, **kwargs):
        pass

    def add_series(self, series, *args, **kwargs):
        line = self._plot.plot(series.index, series.values,
                               color=next(self.colorcycle)['color'],
                               label=series.name)
        self._lines[id(series)] = line
        self.draw()
        return line

    def remove_series(self, series):
        sid = id(series)
        if sid not in self._lines:
            return
        line = self._lines[sid]  # type: Line2D
        line.remove()
        del self._lines[sid]

    def draw(self) -> None:
        self._canvas.draw()

    def clear(self) -> None:
        for sid in [s for s in self._lines]:
            item = self._lines[sid]
            item.remove()
            del self._lines[sid]

    def get_ylim(self):
        return self._plot.get_ylim()

    def get_xlim(self):
        return self._plot.get_xlim()
