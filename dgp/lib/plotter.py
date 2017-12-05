# coding: utf-8

"""
Class to handle Matplotlib plotting of data to be displayed in Qt GUI
"""

from dgp.lib.etc import gen_uuid

import logging
import datetime
from collections import namedtuple
from typing import List, Dict, Tuple, Union

from PyQt5.QtWidgets import QSizePolicy, QMenu, QAction, QWidget, QToolBar
from PyQt5.QtCore import pyqtSignal, QMimeData
from PyQt5.QtGui import QCursor, QDropEvent, QDragEnterEvent, QDragMoveEvent
from matplotlib.backends.backend_qt5agg import (
   FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.dates import DateFormatter, num2date, date2num
from matplotlib.ticker import NullFormatter, NullLocator, AutoLocator
from matplotlib.backend_bases import MouseEvent, PickEvent
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
from matplotlib.text import Annotation
import numpy as np

from dgp.lib.project import Flight
from dgp.gui.dialogs import SetLineLabelDialog
import dgp.lib.types as types


_log = logging.getLogger(__name__)


class AxesGroup:
    """
    AxesGroup conceptually groups a set of sub-plot Axes together, and allows
    for easier operations on multiple Axes at once, especially when dealing
    with plot Patches and Annotations.

    Parameters
    ----------
    *axes : List[Axes]
        Positional list of 1 or more Axes (sub-plots) to add to this AxesGroup
    twin : bool, Optional
        If True, create 'twin' subplots for each of the passed plots, sharing
        the X-Axis.
        Default : False

    Attributes
    ----------
    axes : Dict[int, Axes]
        Dictionary of Axes objects keyed by int Index
    twins : Union[Dict[int, Axes], None]
        If the AxesGroup is initialized with twin=True, the resultant twinned
        Axes objects are stored here, keyed by int Index matching that of
        their parent Axes.
    patches : Dict[str, PatchGroup]
        Dictionary of PatchGroups keyed by the groups UID
        PatchGroups contain partnered Rectangle Patches which are displayed
        at the same location across all active primary Axes.
    patch_pct : Float
        Percentage width of Axes to initially create Patch Rectangles

    """

    def __init__(self, *axes, twin=False):
        assert len(axes) >= 1
        self.axes = dict(enumerate(axes))  # type: Dict[int, Axes]
        self._ax0 = self.axes[0]
        if twin:
            self.twins = {i: ax.twinx() for i, ax in enumerate(axes)}
        else:
            self.twins = None

        self.patches = {}  # type: Dict[str, PatchGroup]
        self.patch_pct = 0.05

        self._active = None  # type: PatchGroup

    def __contains__(self, item: Axes):
        if item in self.axes.values():
            return True
        if self.twins is None:
            return False
        if item in self.twins.values():
            return True

    def on_edge(self, event: MouseEvent):
        xdata = event.xdata
        for pg in self.patches.values():
            if pg.contains(xdata):
                return pg.on_edge(xdata)
            pg.clear_edge()

    def rescale_axes(self, axes: Axes):
        for patch in axes.patches:
            patch.set_visible(False)
        axes.relim(visible_only=True)
        axes.autoscale_view(tight=True)
        for patch in axes.patches:
            patch.set_visible(True)
        for pg in self.patches.values():
            pg.rescale_patches()

    def get_axes(self, index, twin=False):
        if twin and self.twins is not None:
            return self.twins[index]
        return self.axes[index]

    def get_patch(self, xcoord) -> Union['PatchGroup', None]:
        for group in self.patches.values():
            if group.contains(xcoord):
                return group
        return None

    def add_patch(self, xdata, start=None, stop=None, uid=None, label=None) \
            -> Union['PatchGroup', None]:
        """Add a flight line patch at the specified x-coordinate on all axes
        When a user clicks on the plot, we want to place a rectangle,
        centered on the mouse click x-location, and spanning across any
        primary axes in the AxesGroup.

        Parameters
        ----------
        xdata : int
            X location on the Axes to add a new patch
        start, stop : float, optional
            If specified, draw a custom patch from saved data
        uid : str, optional
            If specified, assign the patch group a custom UID
        label : str, optional
            If specified, add the label text as an annotation on the created
            patch group

        Returns
        -------
        New Patch Group : PatchGroup
            Returns newly created group of 'partnered' or linked Rectangle
            Patches as a PatchGroup
            If the PatchGroup is not created sucessfully (i.e. xdata was too
            close to another patch) None is returned.

        """
        if start and stop:
            # Reapply a saved patch
            pg = PatchGroup(uid=uid, parent=self)
            x0 = date2num(start)
            x1 = date2num(stop)
            width = x1 - x0
            for i, ax in self.axes.items():
                ylim = ax.get_ylim()
                height = abs(ylim[1]) + abs(ylim[0])
                rect = Rectangle((x0, ylim[0]), width, height * 2, alpha=0.1)
                patch = ax.add_patch(rect)
                ax.draw_artist(patch)
                pg.add_patch(i, patch)
            if label is not None:
                pg.set_label(label)
            self.patches[pg.uid] = pg
            return pg

        # Check if click is too close to existing patch groups
        for group in self.patches.values():
            if group.contains(xdata, prox=(group.width * 0.3)):
                print("New rectangle too close to add")
                return

        pg = PatchGroup(parent=self)

        xlim = self._ax0.get_xlim()  # type: Tuple
        width = (xlim[1] - xlim[0]) * np.float64(self.patch_pct)
        # x0, y0 = Bottom left corner coordinate
        x0 = xdata - width / 2

        for i, ax in self.axes.items():
            ylim = ax.get_ylim()
            height = ylim[1] - ylim[0]
            rect = Rectangle((x0, ylim[0]), width, height*2, alpha=0.1)
            patch = ax.add_patch(rect)
            ax.draw_artist(patch)
            pg.add_patch(i, patch)
        self.patches[pg.uid] = pg
        return pg

    def remove_pg(self, pg: 'PatchGroup'):
        del self.patches[pg.uid]


class PatchGroup:
    """
    Contain related patches that are cloned across multiple sub-plots
    """
    def __init__(self, label: str=None, uid=None, parent=None):
        self.parent = parent  # type: AxesGroup
        if uid is not None:
            self.uid = uid
        else:
            self.uid = gen_uuid('ptc')
        self.label = label
        self.modified = False
        self.animated = False

        self._patches = {}  # type: Dict[int, Rectangle]
        self._labels = {}  # type: Dict[int, Annotation]
        self._bgs = {}
        self._width = 0
        self._x0 = 0

    @property
    def x(self):
        for patch in self._patches.values():
            return patch.get_x()

    @property
    def width(self):
        """Return the width of the patches in this group (all patches have
        same width)"""
        return self._width

    def contains(self, xdata, prox=0.0005):
        """Check if an x-coordinate is contained within the bounds of this
        patch group, with an optional proximity modifier."""
        return self._x0 - prox <= xdata <= self._x0 + self._width + prox

    def add_patch(self, plot_index: int, patch: Rectangle):
        self._width = patch.get_width()
        self._x0 = patch.get_x()
        self._patches[plot_index] = patch
        patch.figure.canvas.draw()

    def remove(self):
        """Delete this patch group and associated labels from the axes's"""
        for patch in self._patches.values():
            patch.remove()
        for label in self._labels.values():
            label.remove()
        if self.parent is not None:
            self.parent.remove_pg(self)

    def start(self):
        for patch in self._patches.values():
            return num2date(patch.get_x())

    def stop(self):
        for patch in self._patches.values():
            return num2date(patch.get_x() + patch.get_width())

    def clear_edge(self):
        for patch in self._patches.values():
            if patch.get_edgecolor() is not None:
                patch.set_edgecolor(None)
                patch.set_linewidth(None)
                patch.axes.draw_artist(patch)

    def on_edge(self, xdata, prox=0.0005) -> Union[str, None]:
        """
        Check if the xdata location is near the edge of this PatchGroup.
        If the location is near an edge (within prox radius), change the edge
        color of the patch, then return which edge (left/right) we're on.

        Parameters
        ----------
        xdata : float
            X location of event
        prox : float, optional
            Float proximity in Axes units to trigger an edge hit.

        Returns
        -------
        Union[str, None]
            Returns 'left' or 'right' if near the left or right edge of the
            patch, otherwise None

        """
        patch = self._patches[0]
        left = patch.get_x()
        right = left + patch.get_width()
        if left - prox <= xdata <= left + prox:
            for _patch in self._patches.values():
                _patch.set_edgecolor('red')
                _patch.set_linewidth(2)
                _patch.axes.draw_artist(_patch)
            return 'left'
        elif right - prox <= xdata <= right + prox:
            for _patch in self._patches.values():
                _patch.set_edgecolor('blue')
                _patch.set_linewidth(2)
                _patch.axes.draw_artist(_patch)
            return 'right'
        else:
            self.clear_edge()
            return None

    def animate(self) -> None:

        for i, patch in self._patches.items():  # type: int, Rectangle
            patch.set_animated(True)
            # Save original loc/width on animation
            self._x0 = patch.get_x()
            self._width = patch.get_width()
            try:
                self._labels[i].set_animated(True)
            except KeyError:
                pass
            canvas = patch.figure.canvas
            # Need to draw the canvas once after animating to remove the
            # animated patch from the bbox - but this introduces lag.
            # canvas.draw()
            bg = canvas.copy_from_bbox(patch.axes.bbox)
            self._bgs[i] = bg
            canvas.restore_region(bg)
            patch.axes.draw_artist(patch)
            canvas.blit(patch.axes.bbox)

            # This is slow - but would remove original square while dragging
            # patch.figure.canvas.draw()
        self.animated = True
        return

    def unanimate(self) -> None:
        for patch in self._patches.values():
            patch.set_animated(False)
            patch.axes.draw_artist(patch)
            self._x0 = patch.get_x()
            self._width = patch.get_width()
        for label in self._labels.values():
            label.set_animated(False)

        self._bgs = {}
        self.animated = False
        return

    def set_label(self, label: str):
        self.label = label
        for i, patch in self._patches.items():
            px = patch.get_x() + patch.get_width() * 0.5
            ylims = patch.axes.get_ylim()
            py = ylims[0] + abs(ylims[1] - ylims[0]) * 0.5

            annotation = patch.axes.annotate(label,
                xy=(px, py), weight='bold', fontsize=6, ha='center',
                va='center', annotation_clip=False)
            self._labels[i] = annotation
        self.modified = True

    def _update_label(self, index, x, y):
        label = self._labels.get(index, None)
        if label is None:
            return
        label.set_position((x, y))
        label.axes.draw_artist(label)

    def move_patches(self, dx):
        for i in self._patches:
            patch = self._patches[i]  # type: Rectangle
            patch.set_x(self._x0 + dx)

            canvas = patch.figure.canvas  # type: FigureCanvas
            canvas.restore_region(self._bgs[i])
            # Must draw_artist after restoring region, or they will be hidden
            patch.axes.draw_artist(patch)

            cx, cy = self._patch_center(patch)
            self._update_label(i, cx, cy)

            canvas.blit(patch.axes.bbox)
            self.modified = True

    @staticmethod
    def _patch_center(patch):
        cx = patch.get_x() + patch.get_width() * 0.5
        ylims = patch.axes.get_ylim()
        cy = ylims[0] + abs(ylims[1] - ylims[0]) * 0.5
        return cx, cy

    def stretch_patches(self, side, dx):
        if side not in {'left', 'right'}:
            return
        for i, patch in self._patches.items():
            if side == 'left' and self._width - dx > 0:
                patch.set_x(self._x0 + dx)
                patch.set_width(self._width - dx)
            if side == 'right' and self._width + dx > 0:
                patch.set_width(self._width + dx)

            axes = patch.axes
            cx, cy = self._patch_center(patch)
            canvas = patch.figure.canvas
            canvas.restore_region(self._bgs[i])
            axes.draw_artist(patch)
            self._update_label(i, cx, cy)

            canvas.blit(axes.bbox)

        self.modified = True

    def rescale_patches(self):
        """Adjust Height based on new axes limits"""
        for patch in self._patches.values():
            ylims = patch.axes.get_ylim()
            height = ylims[1] - ylims[0]
            patch.set_y(ylims[0])
            patch.set_height(height)
            patch.axes.draw_artist(patch)


class BasePlottingCanvas(FigureCanvas):
    """
    BasePlottingCanvas sets up the basic Qt Canvas parameters, and is designed
    to be subclassed for different plot types.
    """
    def __init__(self, parent=None, width=8, height=4, dpi=100):
        _log.info("Initializing BasePlottingCanvas")

        fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        super().__init__(fig)

        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self._plots = {}
        self._twins = {}
        self._plot_params = {}

        self.figure.canvas.mpl_connect('button_press_event', self.onclick)
        self.figure.canvas.mpl_connect('button_release_event', self.onrelease)
        self.figure.canvas.mpl_connect('motion_notify_event', self.onmotion)
        self.figure.canvas.mpl_connect('pick_event', self.onpick)

    @property
    def axes(self):
        return [ax for ax in self._plots.values()]

    def set_plots(self, rows: int, cols=1, sharex=True) -> None:
        """
        Sets the figure layout with a number of sub-figures and twin figures
        as specified in the arguments.
        The sharex and sharey params control the behavior of the sub-plots,
        with sharex=True all plots will be linked together on the X-Axis
        which is useful for showing/comparing linked data sets.
        The sharey param in fact generates an extra sub-plot/Axes object for
        each plot, overlayed on top of the original. This allows the plotting of
        multiple data sets of different magnitudes on the same chart,
        displaying a scale for each on the left and right edges.

        Parameters
        ----------
        rows: int
            Number plots to generate for display in a vertical stack
        cols: int, optional
            For now, cols will always be 1 (ignored param)
            In future would like to enable dynamic layouts with multiple
            columns as well as rows
        sharex: bool, optional
            Default True. All plots will share their X axis with each other.

        Returns
        -------
        None
        """
        self.figure.clf()
        plots = {}  # dict of plots indexed by int

        # Subplot index starts at 0
        for i in range(1, rows+1):
            if sharex and i > 1:
                plot = self.figure.add_subplot(rows, 1, i, sharex=plots[0])
            else:
                plot = self.figure.add_subplot(rows, 1, i)  # type: Axes
            plot.grid(True)
            plots[i-1] = plot

        # sp.callbacks.connect('xlim_changed', self._on_xlim_changed)
        # sp.callbacks.connect('ylim_changed', self._on_ylim_changed)

        self._plot_params.update({'rows': rows, 'cols': cols, 'sharex':
                                  sharex})

        self._plots = plots

    def clear(self):
        pass

    def onclick(self, event: MouseEvent):
        pass

    def onpick(self, event: PickEvent):
        pass

    def onrelease(self, event: MouseEvent):
        pass

    def onmotion(self, event: MouseEvent):
        pass

    def __len__(self) -> int:
        return len(self._plots)

    def __iter__(self) -> Axes:
        for plot in self._plots.values():
            yield plot

    def __getitem__(self, item) -> Axes:
        return self._plots[item]


LineUpdate = namedtuple('LineUpdate', ['flight_id', 'action', 'uid', 'start',
                                       'stop', 'label'])


class LineGrabPlot(BasePlottingCanvas, QWidget):
    """
    LineGrabPlot implements BasePlottingCanvas and provides an onclick method to
    select flight line segments.
    """

    line_changed = pyqtSignal(LineUpdate)

    def __init__(self, flight: Flight, n: int=1, title=None, parent=None):
        super().__init__(parent=parent)
        # Set initial sub-plot layout
        self.set_plots(rows=n)

        # Experimental patch feature
        self.ax_grp = AxesGroup(*self.axes, twin=True)
        self._selected_group = None  # type: PatchGroup
        self._click_loc = None

        # Experimental
        self.setAcceptDrops(False)
        # END Experimental
        self.plotted = False
        self._zooming = False
        self._panning = False
        self._flight = flight  # type: Flight

        # Resampling variables
        self.timespan = datetime.timedelta(0)
        self.resample = slice(None, None, 20)

        # Map of Line2D objects active in sub-plots, keyed by data UID
        self._lines = {}  # {uid: Line2D, ...}

        if title:
            self.figure.suptitle(title, y=1)
        else:
            self.figure.suptitle(flight.name, y=1)

        self._stretching = None

        # create context menu
        self._pop_menu = QMenu(self)
        self._pop_menu.addAction(QAction('Remove', self,
            triggered=self._remove_patch))
        # self._pop_menu.addAction(QAction('Set Label', self,
        #     triggered=self._label_patch))
        self._pop_menu.addAction(QAction('Set Label', self,
            triggered=self._label_patch))

    def _remove_patch(self, *args):
        # PyQt Slot
        if self._selected_group is not None:
            pg = self._selected_group
            pg.remove()
            self.line_changed.emit(LineUpdate(flight_id=self._flight.uid,
                                              action='remove', uid=pg.uid,
                                              start=pg.start(), stop=pg.stop(),
                                              label=None))
            self._selected_group = None
            self.draw()
        return

    def _label_patch(self):
        # PyQt Slot
        if self._selected_group is not None:
            pg = self._selected_group
            if pg.label is not None:
                dialog = SetLineLabelDialog(pg.label)
            else:
                dialog = SetLineLabelDialog(None)
            if dialog.exec_():
                label = dialog.label_text
            else:
                return

            pg.set_label(label)
            update = LineUpdate(flight_id=self._flight.uid, action='modify',
                                uid=pg.uid, start=pg.start(), stop=pg.stop(),
                                label=pg.label)
            self.line_changed.emit(update)
            self.draw()
        self._selected_group = None
        return

    def add_patch(self, start, stop, uid, label=None):
        if not self.plotted:
            self.draw()
        self.ax_grp.add_patch(0, start=start, stop=stop, uid=uid, label=label)

    def draw(self):
        super().draw()
        self.plotted = True

    def clear(self):
        """Clear the canvas without resetting all of the axes properties."""
        raise NotImplementedError("Clear not properly implemented, do not use")
        self.resample = slice(None, None, 20)
        self.draw()  # Why did I call draw() here?
        for ax in self.axes:  # type: Axes
            # for line in ax.lines[:]:
            #     ax.lines.remove(line)
            for patch in ax.patches[:]:
                patch.remove()
            ax.relim()
        for line in self._lines.values():  # type: Line2D
            # TODO: How to notify/update DataChannel of unplotting
            line.remove()

        self.draw()
        self.plotted = False

    # Issue #36 Enable data/channel selection and plotting
    def add_series(self, dc: types.DataChannel, axes_idx: int=0, draw=True):
        """Add one or more data series to the specified axes as a line plot."""
        if len(self._lines) == 0:
            # If there are 0 plot lines we need to reset the locator/formatter
            _log.debug("Adding locator and major formatter to empty plot.")
            self.axes[0].xaxis.set_major_locator(AutoLocator())
            self.axes[0].xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))

        axes = self[axes_idx]
        color = 'blue'

        if len(axes.lines):
            _log.debug("Base axes already has line, getting twin")
            axes = self.ax_grp.get_axes(axes_idx, twin=True)
            # axes = axes.twinx()
            # self._twins[axes_idx] = axes
            color = 'orange'

        series = dc.series()
        # dc.plotted = axes_idx
        dc.plot(axes_idx)
        line_artist = axes.plot(series.index, series.values,
                                color=color, label=dc.label)[0]
        axes.tick_params('y', colors=color)
        axes.set_ylabel(dc.label, color=color)

        self._lines[dc.uid] = line_artist

        self.ax_grp.rescale_axes(axes)

        if draw:
            self.figure.canvas.draw()

    def remove_series(self, dc: types.DataChannel):
        if dc.uid not in self._lines:
            _log.warning("Series UID could not be located in plot_lines")
            return
        line = self._lines[dc.uid]  # type: Line2D

        axes = line.axes
        axes.lines.remove(line)
        axes.tick_params('y', colors='black')
        axes.set_ylabel('')

        self.ax_grp.rescale_axes(axes)
        del self._lines[dc.uid]
        # dc.plotted = -1
        dc.plot(None)

        if not len(self._lines):
            _log.warning("No Lines on any axes.")
            self.axes[0].xaxis.set_major_locator(NullLocator())
            self.axes[0].xaxis.set_major_formatter(NullFormatter())

        self.draw()

    def get_series_by_label(self, label: str):
        pass

    # Testing: Maybe way to optimize rectangle selection/dragging code
    def onpick(self, event: PickEvent):
        # Pick needs to be enabled for artist ( picker=True )
        # event.artist references the artist that triggered the pick
        _log.debug("Picked artist: {artist}".format(artist=event.artist))

    def onclick(self, event: MouseEvent):
        # First check conditions to see if we need to handle the click.
        if not self.plotted or not len(self._lines):
            return
        # Don't do anything when zooming/panning is enabled
        if self._zooming or self._panning:
            return

        if event.inaxes not in self.ax_grp:
            return

        _log.info("Axes Click @ xdata: {}".format(event.xdata))
        self._click_loc = event.xdata
        self._stretching = None

        # Get PatchGroup at x-loc, or False if none exists
        pg = self.ax_grp.get_patch(event.xdata)
        if pg is not None:
            _log.info("Selected PatchGroup: {}".format(pg.uid))
            self._selected_group = pg

        if event.button == 3:
            # Right Click
            if pg is not None:
                cursor = QCursor()
                self._pop_menu.popup(cursor.pos())
            return

        elif event.button == 1:
            # Left click
            if pg is not None:
                # Already have patches here, animate them
                pg.animate()
                self._stretching = pg.on_edge(event.xdata)
                # event.canvas.draw()
                # self.figure.canvas.draw()
                return

            # Create new PatchGroup
            pg = self.ax_grp.add_patch(event.xdata)
            if pg is None:
                _log.warning("Failed to create Patches, too close?")
                return
            self._selected_group = None

            if self._flight.uid is not None:
                self.line_changed.emit(
                    LineUpdate(flight_id=self._flight.uid, action='add',
                               uid=pg.uid, start=pg.start(), stop=pg.stop(),
                               label=None))

            self.figure.canvas.draw()
            return
        else:
            # Middle Click
            print("Middle click not supported.")
            return

    def onmotion(self, event: MouseEvent):
        if event.inaxes not in self.ax_grp:
            return

        if self._selected_group is not None:
            dx = event.xdata - self._click_loc
            if self._stretching is not None:
                self._selected_group.stretch_patches(self._stretching, dx)
            else:
                self._selected_group.move_patches(dx)
            return
        # Paint edges of rectangle
        self.ax_grp.on_edge(event)

        event.canvas.draw()
        return

    def onrelease(self, event: MouseEvent):
        if self._selected_group is not None:
            pg = self._selected_group  # type: PatchGroup
            if pg.modified:
                update = LineUpdate(flight_id=self._flight.uid,
                                    action='modify', uid=pg.uid,
                                    start=pg.start(), stop=pg.stop(),
                                    label=pg.label)
                self.line_changed.emit(update)
                pg.modified = False
            if pg.animated:
                pg.unanimate()
            self._selected_group = None

            self.figure.canvas.draw()

        self._stretching = None
        self._click_loc = None

    def toggle_zoom(self):
        if self._panning:
            self._panning = False
        self._zooming = not self._zooming

    def toggle_pan(self):
        if self._zooming:
            self._zooming = False
        self._panning = not self._panning

    # EXPERIMENTAL Drag-n-Drop handlers
    def dragEnterEvent(self, event: QDragEnterEvent):
        print("Drag entered widget")
        event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        print("Drag moved")
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        print("Drop detected")
        event.acceptProposedAction()
        print(event.source())
        print(event.pos())
        mime = event.mimeData()  # type: QMimeData
        print(mime)
        print(mime.text())
    # END EXPERIMENTAL Drag-n-Drop

    @staticmethod
    def get_time_delta(x0, x1):
        """Return a time delta from a plot axis limit"""
        return num2date(x1) - num2date(x0)

    def _on_xlim_changed(self, changed: Axes) -> None:
        """
        When the xlim changes (width of the graph), we want to apply a
        decimation algorithm to the dataset to speed up the visual
        performance of the graph. So when the graph is zoomed out we will
        plot only one in 20 data points, and as the graph is zoomed we will
        lower the decimation factor to zero.
        Parameters
        ----------
        changed

        Returns
        -------
        None
        """
        raise NotImplementedError("Need to update this for new properties")
        # TODO: Fix to use new self._lines definition
        _log.info("XLIM Changed!")
        delta = self.get_time_delta(*changed.get_xlim())
        if self.timespan:
            ratio = delta/self.timespan * 100
        else:
            ratio = 100

        if 50 < ratio:
            resample = slice(None, None, 20)
        elif 10 < ratio <= 50:
            resample = slice(None, None, 10)
        else:
            resample = slice(None, None, None)
        if resample == self.resample:
            return

        self.resample = resample

        # Update line data using new resample rate
        for ax in self:
            if self._lines.get(id(ax), None) is not None:
                # print(self._lines[id(ax)])
                for line, series in self._lines[id(ax)]:
                    r_series = series[self.resample]
                    line[0].set_ydata(r_series.values)
                    line[0].set_xdata(r_series.index)
                    ax.draw_artist(line[0])
                    _log.debug("Resampling to: {}".format(self.resample))
            ax.relim()
            ax.get_xaxis().set_major_formatter(DateFormatter('%H:%M:%S'))
        self.figure.canvas.draw()

    def get_toolbar(self, parent=None) -> QToolBar:
        """
        Get a Matplotlib Toolbar for the current plot instance, and set toolbar
        actions (pan/zoom) specific to this plot toolbar.actions() supports
        indexing, with the following default buttons at the specified index:
        1: Home
        2: Back
        3: Forward
        4: Pan
        5: Zoom
        6: Configure Sub-plots
        7: Edit axis, curve etc..
        8: Save the figure

        Parameters
        ----------
        parent : QtWidget, optional
            Optional Qt Parent for this object

        Returns
        -------
        QtWidgets.QToolBar
            Matplotlib Qt Toolbar used to control this plot instance
        """
        toolbar = NavigationToolbar(self, parent=parent)
        toolbar.actions()[4].triggered.connect(self.toggle_pan)
        toolbar.actions()[5].triggered.connect(self.toggle_zoom)
        return toolbar
