# coding: utf-8

# PROTOTYPE for new Axes Manager class

import logging
from itertools import cycle, count, chain
from typing import Union, Tuple, Dict, List
from datetime import datetime, timedelta

import PyQt5.QtCore as QtCore

from pandas import Series
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.dates import DateFormatter, date2num, num2date
from matplotlib.ticker import AutoLocator, ScalarFormatter, Formatter
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.gridspec import GridSpec
from matplotlib.backend_bases import MouseEvent, PickEvent
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

from dgp.lib.etc import gen_uuid

__all__ = ['StackedAxesManager', 'PatchManager', 'RectanglePatchGroup']
_log = logging.getLogger(__name__)
EDGE_PROX = 0.002

"""
Notes/Thoughts WIP:

What to do in instances where 2 data sets with greatly different X-ranges are 
plotted together? Or some way to disallow this/screen when importing gps/grav.
E.g. when importing a GPS file when gravity is already present show warning 
if the min/max values respectively differ by some percentage?
"""
COLOR_CYCLE = ['red', 'blue', 'green', 'orange', 'purple']


def _pad(xy0: float, xy1: float, pct=0.05):
    """Pads a given x/y limit pair by the specified percentage (as
    float), and returns a tuple of the new values.

    Parameters
    ----------
    xy0, xy1 : float
        Limit values that correspond to the left/bottom and right/top
        X or Y Axes limits respectively.
    pct : float, optional
        Percentage value by which to pad the supplied limits.
        Default: 0.05 (5%)
    """
    magnitude = abs(xy1) - abs(xy0)
    pad = magnitude * pct
    return xy0 - pad, xy1 + pad


# TODO: This is not general enough
# Plan to create a StackedMPLWidget and StackedPGWidget which will contain
# Matplotlib subplot-Axes or pyqtgraph PlotItems.
# The xWidget will provide the Qt Widget to be added to the GUI, and provide
# methods for interacting with plots on specific rows.
class StackedAxesManager:
    """
    StackedAxesManager is used to generate and manage a subplots on a
    Matplotlib Figure. A specified number of subplots are generated and
    displayed in rows (possibly add ability to add columns later).
    The AxesManager provides an API to draw lines on specified axes rows,
    and provides a means to track and update/change lines based on their
    original Pandas Series data.

    Parameters
    ----------
    figure : Figure
        MPL Figure to create subplots (Axes) objects upon
    rows : int, Optional
        Number of rows of subplots to generate on the figure.
        Default is 1
    xformatter : matplotlib.ticker.Formatter, optional
        Supply a custom ticker Formatter for the x-axis, or use the default
        DateFormatter.

    Notes (WIP)
    -----------

    AxesManager should create and manage a set of subplots displayed in a
    rows. A twin-x axis is then 'stacked' behind each base axes on each row.
    The manager should be general enough to support a number of use-cases:
        1. Line Grab Plot interface - user clicks on plots to add a rectangle
        patch which is drawn at the same x-loc on all axes in the group
        (uses PatchGroup class)
            This plot uses Date indexes
        2. Transform Plot - 2 or more stacked plots used to plot data,
        possibly indexed against a Date, or possibly indexed by lat/longitude.
        This plot would not require line selection patches.

        In future would like to add ability to have a data 'inspection' line
        - i.e. move mouse over and a text box will pop up with a vertical
        line through the data, showing the value at intersection - don't know
        proper name for that

        Add ability to switch xformatter without re-instantiating the Manager?
        e.g. Plotting gravity vs time, then want to clear off time data and
        plot grav vs long. Maybe auto-clear all lines/data from plot and
        switch x-axis formatter.

    """
    def __init__(self, figure, rows=1, xformatter=None):
        self.figure = figure
        self.axes = {}  # type: Dict[int: (Axes, Axes)]
        self._axes_color = {}
        self._inset_axes = {}

        self._lines = {}
        self._line_data = {}
        self._line_lims = {}
        self._line_id = count(start=1, step=1)

        self._base_x_lims = None
        self._rows = rows
        self._cols = 1
        self._padding = 0.05

        self._xformatter = xformatter or DateFormatter('%H:%M:%S')

        spec = GridSpec(nrows=self._rows, ncols=self._cols)

        x0 = date2num(datetime.now())
        x1 = date2num(datetime.now() + timedelta(hours=1))
        self._ax0 = figure.add_subplot(spec[0])  # type: Axes
        self.set_xlim(x0, x1)

        for i in range(0, rows):
            if i == 0:
                ax = self._ax0
            else:
                ax = figure.add_subplot(spec[i], sharex=self._ax0)
            if i == rows - 1:
                ax.xaxis.set_major_locator(AutoLocator())
                ax.xaxis.set_major_formatter(self._xformatter)
            else:
                for lbl in ax.get_xticklabels():
                    lbl.set_visible(False)

            ax.autoscale(False)
            ax.grid(True)
            twin = ax.twinx()
            self.axes[i] = ax, twin
            self._axes_color[i] = cycle(COLOR_CYCLE)

    def __len__(self):
        """Return number of primary Axes managed by this Class"""
        return len(self.axes)

    def __contains__(self, axes):
        flat = chain(*self.axes.values())
        return axes in flat

    def __getitem__(self, index) -> Tuple[Axes, Axes]:
        """Return (Axes, Twin) pair at the given row index."""
        if index not in self.axes:
            raise IndexError
        return self.axes[index]

    # Experimental
    def add_inset_axes(self, row, position='upper right', height='15%',
                       width='15%', labels=False, **kwargs) -> Axes:
        """Add an inset axes on the base axes at given row
        Default is to create an inset axes in the upper right corner, with height and width of 15% of the parent.

        This inset axes can be used for example to show the zoomed-in position of the main graph in relation to the
        overall data.
        """
        try:
            return self._inset_axes[row]
        except KeyError:
            pass

        position_map = {
            'upper right': 1,
            'upper left': 2,
            'lower left': 3,
            'lower right': 4,
            'right': 5,
            'center left': 6,
            'center right': 7,
            'lower center': 8,
            'upper center': 9,
            'center': 10
        }
        base_ax = self.get_axes(row)
        if labels:
            axes_kwargs = kwargs
        else:
            axes_kwargs = dict(xticklabels=[], yticklabels=[])
            axes_kwargs.update(kwargs)

        axes = inset_axes(base_ax, height, width, loc=position_map.get(
            position, 1), axes_kwargs=axes_kwargs)
        self._inset_axes[row] = axes
        return axes

    def get_inset_axes(self, row) -> Union[Axes, None]:
        """Retrieve Inset Axes for the primary Axes at specified row.
        Note - support is currently only for a single inset axes per row."""
        return self._inset_axes.get(row, None)

    def get_axes(self, row, twin=False) -> Axes:
        """Explicity retrieve an Axes from the given row, returning the Twin
        axes if twin is True

        Notes
        -----
        It is obviously possible to plot directly to the Axes returned by
        this method, however you then give up the state tracking mechanisms
        provided by the StackedAxesManager class, and will be responsible for
        manually manipulating and scaling the Axes.
        """
        ax0, ax1 = self.axes[row]
        if twin:
            return ax1
        return ax0

    def add_series(self, series, row=0, uid=None, redraw=True,
                   fit='common', **plot_kwargs):
        """
        Add and track a Pandas data Series to the specified subplot.

        Notes
        -----
        Note on behavior, add_series will automatically select the least
        populated axes of the pair (primary and twin-x) to plot the new
        channel on, and if it is a tie will default to the primary.

        Parameters
        ----------
        series : Series
            Pandas data Series with index and values, to be plotted as x and y
            respectively
        row : int
            Row index of the Axes to plot on
        uid : str, optional
            Optional UID to reference series by within Axes Manager,
            else numerical ID will be assigned and returned by this function.
        redraw : bool
            If True, call figure.canvas.draw(), else the caller must ensure
            to redraw the canvas at some point.
        fit : EXPERIMENTAL
            Keyword to determine x-axis fitting when data sets are different
            lengths.
            Options: (WIP)
                common : fit x-axis to show common/overlapping data
                    What if there is no overlap?
                inclusive : fit x-axis to all data
                first : fit x-axis based on the first plotted data set
                last : re-fit x-axis on latest data set
        plot_kwargs : dict, optional
            Optional dictionary of keyword arguments to be passed to the
            Axes.plot method

        Returns
        -------
        Union[str, int] :
            UID of plotted channel

        """
        axes, twin = self.axes[row]
        # Select least populated Axes
        if len(axes.lines) <= len(twin.lines):
            ax = axes
        else:
            ax = twin

        uid = uid or next(self._line_id)

        # Set the x-limits range if it hasn't been set yet
        # We're assuming that all plotted data will conform to the same
        # time-span currently, this behavior may need to change (esp if we're
        #  not dealing with time?)
        x0, x1 = series.index.min(), series.index.max()
        try:
            x0 = date2num(x0)
            x1 = date2num(x1)
        except AttributeError:
            pass

        if self._base_x_lims is None:
            self.set_xlim(x0, x1)
            self._base_x_lims = x0, x1
        else:
            # TODO: Test/consider this logic - is it the desired behavior
            # e.g. two datasets (gps/grav) where gravity is 1hr longer than GPS,
            # should we auto-scale the x-axis to fit all of the data,
            # or to the shortest? maybe give an option?
            base_x0, base_x1 = self._base_x_lims
            min_x0 = min(base_x0, x0)
            max_x1 = max(base_x1, x1)
            self.set_xlim(min_x0, max_x1)
            self._base_x_lims = min_x0, max_x1

        y0, y1 = series.min(), series.max()

        color = plot_kwargs.get('color', None) or next(self._axes_color[row])
        line = ax.plot(series.index, series.values, color=color,
                       **plot_kwargs)[0]

        self._lines[uid] = line
        self._line_data[line] = series
        self._line_lims[line] = x0, x1, y0, y1

        ax.set_ylim(*_pad(y0, y1))

        if redraw:
            self.figure.canvas.draw()

        return uid

    def remove_series(self, *series_ids, redraw=True):
        invalids = []
        for uid in series_ids:
            if uid not in self._lines:
                invalids.append(uid)
                continue

            line = self._lines[uid]  # type: Line2D
            ax = line.axes  # type: Axes

            line.remove()
            del self._line_data[line]
            del self._lines[uid]

            if len(ax.lines) == 0:
                ax.set_ylim(-1, 1)
            else:
                # Rescale y if we allow more than 1 line per Axes
                pass

        if redraw:
            self.figure.canvas.draw()

        if invalids:
            raise ValueError("Invalid UID's passed to remove_series: {}"
                             .format(invalids))

    def get_ylim(self, idx, twin=False):
        if twin:
            return self.axes[idx + self._rows].get_ylim()
        return self.axes[idx].get_ylim()

    # TODO: Resample logic
    def subsample(self, step):
        """Resample all lines in all Axes by slicing with step."""

        pass

    def set_xlim(self, left: float, right: float, padding=None):
        """Set the base Axes xlims to the specified float values."""
        if padding is None:  # Explicitly check for None, as 0 should be valid
            padding = self._padding
        self._ax0.set_xlim(*_pad(left, right, padding))

    def get_x_ratio(self):
        """Returns the ratio of the current plot width to the base plot width"""
        if self._base_x_lims is None:
            return 1.0
        base_w = self._base_x_lims[1] - self._base_x_lims[0]
        cx0, cx1 = self.axes[0].get_xlim()
        curr_w = cx1 - cx0
        return curr_w / base_w

    def reset_view(self, x_margin=None, y_margin=None):
        """Reset limits of each Axes and Twin Axes to show entire data within
        them"""
        # Test the min/max logic here
        if self._base_x_lims is None:
            return
        min_x0, max_x1 = self._base_x_lims
        for uid, line in self._lines.items():
            ax = line.axes  # type: Axes
            data = self._line_data[line]  # type: Series
            x0, x1, y0, y1 = self._line_lims[line]
            ax.set_ylim(*_pad(y0, y1))

            if not min_x0:
                min_x0 = max(min_x0, x0)
            else:
                min_x0 = min(min_x0, x0)
            max_x1 = max(max_x1, x1)

        self.set_xlim(min_x0, max_x1)


class PatchManager:
    def __init__(self, parent=None):
        self.patchgroups = []  # type: List[RectanglePatchGroup]
        self._active = None
        self._x0 = None  # X location when active group was selected
        self.parent = parent

    @property
    def active(self) -> Union[None, 'RectanglePatchGroup']:
        return self._active

    @property
    def groups(self):
        """Return a sorted list of patchgroups by patch x location."""
        return sorted(self.patchgroups, key=lambda pg: pg.x)

    def valid_click(self, xdata, proximity=0.05):
        """Return True if xdata is a valid location to place a new patch
        group, False if it is too close to an existing patch."""
        pass

    def add_group(self, group: 'RectanglePatchGroup'):
        self.patchgroups.append(group)

    def select(self, xdata, inner=True) -> bool:
        self.deselect()
        for pg in self.groups:
            if xdata in pg:
                pg.animate(xdata)
                self._active = pg
                self._x0 = xdata
                break
        else:
            self._x0 = None

        return self._active is not None

    def deselect(self) -> None:
        if self._active is not None:
            self._active.unanimate()
        self._active = None

    def rescale_patches(self):
        for group in self.patchgroups:
            group.fit_height()

    def onmotion(self, event: MouseEvent) -> None:
        if event.xdata is None:
            return
        if self.active is None:
            self.highlight_edge(event.xdata)
            event.canvas.draw()
        else:
            dx = event.xdata - self._x0
            self.active.shift_x(dx)

    def highlight_edge(self, xdata: float) -> None:
        """
        Called on motion event if a patch isn't selected. Highlight the edge
        of a patch if it is under the mouse location.
        Return all other edges to black

        Parameters
        ----------
        xdata : float
            Mouse x-location in plot data coordinates

        """
        edge_grp = None
        self.parent.setCursor(QtCore.Qt.ArrowCursor)
        for group in self.groups:
            edge = group.get_edge(xdata, inner=False)
            if edge in ('left', 'right'):

                edge_grp = group
                self.parent.setCursor(QtCore.Qt.SizeHorCursor)
                group.set_edge(edge, 'red', select=False)
                break
        else:
            # group.set_edge('', 'black', select=False)
            self.parent.setCursor(QtCore.Qt.PointingHandCursor)

        for group in self.patchgroups:
            if group is edge_grp:
                continue
            else:
                group.set_edge('', 'black', select=False)


class RectanglePatchGroup:
    """
    Group related matplotlib Rectangle Patches which share an x axis on
    different Axes/subplots.
    Current use case is for Flight-line selection rectangles, but this could
    be expanded.


    Notes/TODO:
    -----------
    Possibly create base PatchGroup class with specialized classes for
    specific functions e.g. Flight-line selection, and data pointer (show
    values on data with vertical line through)

    """
    def __init__(self, *patches, label: str='', uid=None):
        self.uid = uid or gen_uuid('ptc')
        self.label = label
        self._modified = False
        self.animated = False

        self._patches = {i: patch for i, patch in enumerate(patches)}
        self._p0 = patches[0]  # type: Rectangle
        self._labels = {}  # type: Dict[int, Annotation]
        self._bgs = {}
        # Store x location on animation for delta movement
        self._x0 = 0
        # Original width must be stored for stretch
        self._width = 0
        self._stretching = None

        self.fit_height()

    def __contains__(self, x):
        return self.x <= x <= self.x + self.width

    @property
    def modified(self):
        return self._modified

    @property
    def stretching(self):
        return self._stretching

    @property
    def width(self):
        """Return the width of the patches in this group (all patches have
        same width)"""
        return self._p0.get_width()

    @property
    def x(self):
        if self._p0 is None:
            return None
        return self._p0.get_x()

    def animate(self, xdata=None) -> None:
        """
        Animate all artists contained in this PatchGroup, and record the x
        location of the group.
        Matplotlibs Artist.set_animated serves to remove the artists from the
        canvas bbox, so that we can copy a rasterized bbox of the rest of the
        canvas and then blit it back as we move or modify the animated artists.
        This means that a complete redraw only has to be done for the
        selected artists, not the entire canvas.

        """
        _log.debug("Animating patches")
        if self._p0 is None:
            raise AttributeError("No patches exist")
        self._x0 = self._p0.get_x()
        self._width = self._p0.get_width()
        edge = self.get_edge(xdata, inner=False)
        self.set_edge(edge, color='red', select=True)

        for i, patch in self._patches.items():  # type: int, Rectangle
            patch.set_animated(True)
            try:
                self._labels[i].set_animated(True)
            except KeyError:
                pass
            canvas = patch.figure.canvas
            # Need to draw the canvas once after animating to remove the
            # animated patch from the bbox - but this introduces significant
            # lag between the mouse click and the beginning of the animation.
            # canvas.draw()
            bg = canvas.copy_from_bbox(patch.axes.bbox)
            self._bgs[i] = bg
            canvas.restore_region(bg)
            patch.axes.draw_artist(patch)
            canvas.blit(patch.axes.bbox)

        self.animated = True
        return

    def unanimate(self) -> None:
        if not self.animated:
            return
        for patch in self._patches.values():
            patch.set_animated(False)
        for label in self._labels.values():
            label.set_animated(False)

        self._bgs = {}
        self._stretching = None
        self.animated = False
        self._modified = False

    # def add_patch(self, plot_index: int, patch: Rectangle):
    #     if not len(self._patches):
    #         Record attributes of first added patch for reference
            # self._p0 = patch
        # self._patches[plot_index] = patch

    def hide(self):
        for item in chain(self._patches.values(), self._labels.values()):
            item.set_visible(False)

    def show(self):
        for item in chain(self._patches.values(), self._labels.values()):
            item.set_visible(True)

    def contains(self, xdata, prox=EDGE_PROX):
        """Check if an x-coordinate is contained within the bounds of this
        patch group, with an optional proximity modifier."""
        prox = self._scale_prox(prox)
        x0 = self._p0.get_x()
        width = self._p0.get_width()
        return x0 - prox <= xdata <= x0 + width + prox


    def remove(self):
        """Delete this patch group and associated labels from the axes's"""
        self.unanimate()
        for item in chain(self._patches.values(), self._labels.values()):
            item.remove()
        self._p0 = None

    def start(self):
        """Return the start x-location of this patch group as a Date Locator"""
        for patch in self._patches.values():
            return num2date(patch.get_x())

    def stop(self):
        """Return the stop x-location of this patch group as a Data Locator"""
        if self._p0 is None:
            return None
        return num2date(self._p0.get_x() + self._p0.get_width())

    def get_edge(self, xdata, prox=EDGE_PROX, inner=False):
        """Get the edge that the mouse is in proximity to, or None if it is
        not."""
        left = self._p0.get_x()
        right = left + self._p0.get_width()
        prox = self._scale_prox(prox)

        if left - (prox * int(not inner)) <= xdata <= left + prox:
            return 'left'
        if right - prox <= xdata <= right + (prox * int(not inner)):
            return 'right'
        return None

    def set_edge(self, edge: str, color: str, select: bool=False):
        """Set the given edge color, and set the Group stretching factor if
        select"""
        if edge not in {'left', 'right'}:
            color = (0.0, 0.0, 0.0, 0.1)  # black, 10% alpha
            self._stretching = None
        elif select:
            _log.debug("Setting stretch to: {}".format(edge))
            self._stretching = edge
        for patch in self._patches.values():  # type: Rectangle
            if patch.get_edgecolor() != color:
                patch.set_edgecolor(color)
                patch.axes.draw_artist(patch)

    def set_label(self, label: str, index=None) -> None:
        """
        Set the label on these patches. Centered vertically and horizontally.

        Parameters
        ----------
        label : str
            String to label the patch group with.
        index : Union[int, None], optional
            The patch index to set the label of. If None, all patch labels will
            be set to the same value.

        """
        if label is None:
            # Fixes a label being displayed as 'None'
            label = ''

        self.label = label

        if index is not None:
            patches = {index: self._patches[index]}
        else:
            patches = self._patches

        for i, patch in patches.items():
            px = patch.get_x() + patch.get_width() * 0.5
            ylims = patch.axes.get_ylim()
            py = ylims[0] + abs(ylims[1] - ylims[0]) * 0.5

            annotation = patch.axes.annotate(label,
                                             xy=(px, py),
                                             weight='bold',
                                             fontsize=6,
                                             ha='center',
                                             va='center',
                                             annotation_clip=False)
            self._labels[i] = annotation
        self._modified = True

    def fit_height(self) -> None:
        """Adjust Height based on axes limits"""
        for i, patch in self._patches.items():
            ylims = patch.axes.get_ylim()
            height = abs(ylims[1]) + abs(ylims[0])
            patch.set_y(ylims[0])
            patch.set_height(height)
            patch.axes.draw_artist(patch)
            self._move_label(i, *self._patch_center(patch))

    def shift_x(self, dx) -> None:
        """
        Move or stretch patches by dx, action depending on activation
        location i.e. when animate was called on the group.

        Parameters
        ----------
        dx : float
            Delta x, positive or negative float value to move or stretch the
            group

        """
        if self._stretching in ('left', 'right'):
            return self._stretch(dx)
        for i in self._patches:
            patch = self._patches[i]  # type: Rectangle
            patch.set_x(self._x0 + dx)

            canvas = patch.figure.canvas  # type: FigureCanvas
            canvas.restore_region(self._bgs[i])
            # Must draw_artist after restoring region, or they will be hidden
            patch.axes.draw_artist(patch)

            cx, cy = self._patch_center(patch)
            self._move_label(i, cx, cy)

            canvas.blit(patch.axes.bbox)
            self._modified = True

    def _stretch(self, dx) -> None:
        if self._p0 is None:
            return None
        width = self._width
        if self._stretching == 'left' and width - dx > 0:
            for i, patch in self._patches.items():
                patch.set_x(self._x0 + dx)
                patch.set_width(width - dx)
        elif self._stretching == 'right' and width + dx > 0:
            for i, patch in self._patches.items():
                patch.set_width(width + dx)
        else:
            return

        for i, patch in self._patches.items():
            axes = patch.axes
            cx, cy = self._patch_center(patch)
            canvas = patch.figure.canvas
            canvas.restore_region(self._bgs[i])
            axes.draw_artist(patch)
            self._move_label(i, cx, cy)
            canvas.blit(axes.bbox)

        self._modified = True

    def _move_label(self, index, x, y) -> None:
        """
        Move labels in this group to new position x, y

        Parameters
        ----------
        index : int
            Axes index of the label to move
        x, y : int
            x, y location to move the label

        """
        label = self._labels.get(index, None)
        if label is None:
            return
        label.set_position((x, y))
        label.axes.draw_artist(label)

    def _scale_prox(self, pct: float):
        """
        Take a decimal percentage and return the apropriate Axes unit value
        based on the x-axis limits of the current plot.
        This ensures that methods using a proximity selection modifier behave
        the same, independant of the x-axis scale or size.

        Parameters
        ----------
        pct : float
            Percent value expressed as float

        Returns
        -------
        float
            proximity value converted to Matplotlib Axes scale value

        """
        if self._p0 is None:
            return 0
        x0, x1 = self._p0.axes.get_xlim()
        return (x1 - x0) * pct

    @staticmethod
    def _patch_center(patch) -> Tuple[int, int]:
        """Utility method to calculate the horizontal and vertical center
        point of the specified patch"""
        cx = patch.get_x() + patch.get_width() * 0.5
        ylims = patch.axes.get_ylim()
        cy = ylims[0] + abs(ylims[1] - ylims[0]) * 0.5
        return cx, cy


