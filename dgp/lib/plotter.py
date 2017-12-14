# coding: utf-8

"""
Class to handle Matplotlib plotting of data to be displayed in Qt GUI
"""

from dgp.lib.etc import gen_uuid

import logging
from collections import namedtuple
from typing import Dict, Tuple, Union

from PyQt5.QtWidgets import QSizePolicy, QMenu, QAction, QWidget, QToolBar
from PyQt5.QtCore import pyqtSignal, QMimeData
from PyQt5.QtGui import QCursor, QDropEvent, QDragEnterEvent, QDragMoveEvent
import PyQt5.QtCore as QtCore
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
EDGE_PROX = 0.005

# Monkey patch the MPL Nav toolbar home button. We'll provide custom action
# by attaching a event listener to the toolbar action trigger.
# Save the default home method in case another plot desires the default behavior
NT_HOME = NavigationToolbar.home
NavigationToolbar.home = lambda *args: None


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
        expressed as a Float value.

    """

    def __init__(self, *axes, twin=False, parent=None):
        assert len(axes) >= 1
        self.parent = parent
        self.axes = dict(enumerate(axes))  # type: Dict[int, Axes]
        self._ax0 = self.axes[0]
        if twin:
            self.twins = {i: ax.twinx() for i, ax in enumerate(axes)}
        else:
            self.twins = None

        self.patches = {}  # type: Dict[str, PatchGroup]
        self.patch_pct = 0.05

        self._selected = None  # type: PatchGroup
        self._select_loc = None
        self._stretch = None
        self._highlighted = None  # type: PatchGroup

        # Map ax index to x/y limits of original data
        self._base_ax_limits = {}

    def __contains__(self, item: Axes):
        if item in self.axes.values():
            return True
        if self.twins is None:
            return False
        if item in self.twins.values():
            return True

    def __getattr__(self, item):
        """
        Used to get methods in the selected PatchGroup of this AxesGroup,
        if there is one. If there is no selection, we return an empty lambda
        function which takes args/kwargs and returns None.

        This functionality may not be necesarry, as we are dealing with most
        of the selected operatiosn within the AxesGroup now.
        """
        if hasattr(self._selected, item):
            return getattr(self._selected, item)
        else:
            print("_active is None or doesn't have attribute: ", item)
            return lambda *x, **y: None

    @property
    def all_axes(self):
        """Return a list of all Axes objects, including Twin Axes (if they
        exist)"""
        axes = list(self.axes.values())
        if self.twins is not None:
            axes.extend(self.twins.values())
        return axes

    def select(self, xdata, prox=EDGE_PROX, inner=False):
        """
        Select any patch group at the specified xdata location. Return True
        if a PatchGroup was selected, False if there was no group to select.
        Use prox and inner to specify tolerance of selection.

        Parameters
        ----------
        xdata
        prox : float
            Add/subtract the specified width from the right/left edge of the
            patch groups when checking for a hit.
        inner : bool
            Specify whether a patch should enter stretch mode only if the
            click is inside its left/right bounds +/- prox. Or if False,
            set the patch to stretch if the click is just outside of the
            rectangle (within proximity)

        Returns
        -------
        bool:
            True if PatchGroup selected
            False if no PatchGroup at xdata location

        """
        for pg in self.patches.values():
            if pg.contains(xdata, prox):
                self._selected = pg
                edge = pg.get_edge(xdata, prox=prox, inner=inner)
                pg.set_edge(edge, 'red', select=True)
                pg.animate()
                self._select_loc = xdata
                self.parent.setCursor(QtCore.Qt.ClosedHandCursor)
                return True
        else:
            return False

    def deselect(self) -> None:
        """
        Deselect the active PatchGroup (if there is one), and reset the cursor.
        """
        if self._selected is not None:
            self._selected.unanimate()
            self._selected = None
            self.parent.setCursor(QtCore.Qt.PointingHandCursor)

    @property
    def active(self) -> Union['PatchGroup', None]:
        return self._selected

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
        self.parent.setCursor(QtCore.Qt.ArrowCursor)
        if not len(self.patches):
            return
        for patch in self.patches.values():  # type: PatchGroup
            if patch.contains(xdata):
                edge = patch.get_edge(xdata, inner=False)
                if edge is not None:
                    self.parent.setCursor(QtCore.Qt.SizeHorCursor)
                else:
                    self.parent.setCursor(QtCore.Qt.PointingHandCursor)
                patch.set_edge(edge, 'red')
            else:
                patch.set_edge('', 'black')

    def onmotion(self, event: MouseEvent):
        if event.inaxes not in self:
            return
        if self._selected is None:
            self.highlight_edge(event.xdata)
            event.canvas.draw()
        else:
            dx = event.xdata - self._select_loc
            self._selected.move_patches(dx)

    def go_home(self):
        """Autoscale the axes back to the data limits, and rescale patches."""
        for ax in self.all_axes:
            ax.autoscale(True, 'both', False)
        self.rescale_patches()

    def rescale_patches(self):
        """Rescales all Patch Groups to fit their Axes y-limits"""
        for pg in self.patches.values():
            pg.rescale_patches()

    def get_axes(self, index) -> (Axes, bool):
        """
        Get an Axes object at the specified index, or a twin if the Axes at
        the index already has a line plotted in it.
        Boolean is returned with the Axes, specifying whether the returned
        Axes is a Twin or not.

        Parameters
        ----------
        index : int
            Index of the Axes to retrieve.

        Returns
        -------
        Tuple[Axes, bool]:
            Axes object and boolean value
            bool : False if Axes is the base (non-twin) Axes,
                   True if it is a twin

        """
        ax = self.axes[index]
        if self.twins is not None and len(ax.lines):
            return self.twins[index], True
        return ax, False

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
            # Reapply a saved patch from start and stop positions of the rect
            x0 = date2num(start)
            x1 = date2num(stop)
            width = x1 - x0
        else:
            xlim = self._ax0.get_xlim()  # type: Tuple
            width = (xlim[1] - xlim[0]) * np.float64(self.patch_pct)
            x0 = xdata - width / 2

        # Check if click is too close to existing patch groups
        for group in self.patches.values():
            if group.contains(xdata, prox=.04):
                raise ValueError("Flight patch too close to add")

        pg = PatchGroup(uid=uid, parent=self)
        for i, ax in self.axes.items():
            ylim = ax.get_ylim()
            height = abs(ylim[1]) + abs(ylim[0])
            rect = Rectangle((x0, ylim[0]), width, height*2, alpha=0.1,
                             picker=True, edgecolor='black', linewidth=2)
            patch = ax.add_patch(rect)
            ax.draw_artist(patch)
            pg.add_patch(i, patch)

        if label is not None:
            pg.set_label(label)
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
        self._p0 = None     # type: Rectangle
        self._labels = {}   # type: Dict[int, Annotation]
        self._bgs = {}
        # Store x location on animation for delta movement
        self._x0 = 0
        # Original width must be stored for stretch
        self._width = 0
        self._stretching = None

    @property
    def x(self):
        if self._p0 is None:
            return None
        return self._p0.get_x()

    @property
    def stretching(self):
        return self._stretching

    @property
    def width(self):
        """Return the width of the patches in this group (all patches have
        same width)"""
        return self._p0.get_width()

    def hide(self):
        for patch in self._patches.values():
            patch.set_visible(False)
        for label in self._labels.values():
            label.set_visible(False)

    def show(self):
        for patch in self._patches.values():
            patch.set_visible(True)
        for label in self._labels.values():
            label.set_visible(True)

    def contains(self, xdata, prox=EDGE_PROX):
        """Check if an x-coordinate is contained within the bounds of this
        patch group, with an optional proximity modifier."""
        prox = self._scale_prox(prox)
        x0 = self._p0.get_x()
        width = self._p0.get_width()
        return x0 - prox <= xdata <= x0 + width + prox

    def add_patch(self, plot_index: int, patch: Rectangle):
        if not len(self._patches):
            # Record attributes of first added patch for reference
            self._p0 = patch
        self._patches[plot_index] = patch

    def remove(self):
        """Delete this patch group and associated labels from the axes's"""
        self.unanimate()
        for patch in self._patches.values():
            patch.remove()
        for label in self._labels.values():
            label.remove()
        self._p0 = None
        if self.parent is not None:
            self.parent.remove_pg(self)

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
            else:
                break

    def animate(self) -> None:
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
        self._stretching = False
        self.animated = False
        return

    def set_label(self, label: str) -> None:
        """
        Set the label on these patches. Centered vertically and horizontally.

        Parameters
        ----------
        label : str
            String to label the patch group with.

        """
        self.label = label
        for i, patch in self._patches.items():
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
        self.modified = True

    def move_patches(self, dx) -> None:
        """
        Move or stretch patches by dx, action depending on activation
        location i.e. when animate was called on the group.

        Parameters
        ----------
        dx : float
            Delta x, positive or negative float value to move or stretch the
            group

        """
        if self._stretching is not None:
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
            self.modified = True

    def rescale_patches(self) -> None:
        """Adjust Height based on new axes limits"""
        for i, patch in self._patches.items():
            ylims = patch.axes.get_ylim()
            height = abs(ylims[1]) + abs(ylims[0])
            patch.set_y(ylims[0])
            patch.set_height(height)
            patch.axes.draw_artist(patch)
            self._move_label(i, *self._patch_center(patch))

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

        self.modified = True

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


class BasePlottingCanvas(FigureCanvas):
    """
    BasePlottingCanvas sets up the basic Qt FigureCanvas parameters, and is
    designed to be subclassed for different plot types.
    Mouse events are connected to the canvas here, and the handlers should be
    overriden in sub-classes to provide custom actions.
    """
    def __init__(self, parent=None, width=8, height=4, dpi=100):
        _log.debug("Initializing BasePlottingCanvas")

        super().__init__(Figure(figsize=(width, height),
                                dpi=dpi,
                                tight_layout=True))

        self.setParent(parent)
        super().setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        super().updateGeometry()

        self.figure.canvas.mpl_connect('button_press_event', self.onclick)
        self.figure.canvas.mpl_connect('button_release_event', self.onrelease)
        self.figure.canvas.mpl_connect('motion_notify_event', self.onmotion)
        self.figure.canvas.mpl_connect('pick_event', self.onpick)

    def onclick(self, event: MouseEvent):
        pass

    def onpick(self, event: PickEvent):
        pass

    def onrelease(self, event: MouseEvent):
        pass

    def onmotion(self, event: MouseEvent):
        pass


LineUpdate = namedtuple('LineUpdate', ['flight_id', 'action', 'uid', 'start',
                                       'stop', 'label'])


class LineGrabPlot(BasePlottingCanvas, QWidget):
    """
    LineGrabPlot implements BasePlottingCanvas and provides an onclick method to
    select flight line segments.

    Attributes
    ----------
    ax_grp : AxesGroup

    plotted : bool
        Boolean flag - True if any axes have been plotted/drawn to

    """

    line_changed = pyqtSignal(LineUpdate)
    resample = pyqtSignal(int)

    def __init__(self, flight: Flight, rows: int=1, title=None, parent=None):
        super().__init__(parent=parent)
        # Set initial sub-plot layout
        self._plots = self.set_plots(rows=rows, sharex=True, resample=True)
        self.ax_grp = AxesGroup(*self._plots.values(), twin=True, parent=self)

        # Experimental
        self.setAcceptDrops(False)
        # END Experimental
        self.plotted = False
        self._zooming = False
        self._panning = False
        self._flight = flight  # type: Flight

        # Resampling variables
        self._series = {}  # {uid: pandas.Series, ...}
        self._xwidth = 0
        self._ratio = 100
        # Define resampling steps based on integer percent range
        # TODO: Future: enable user to define custom ranges/steps
        self._steps = {
            range(0, 15): slice(None, None, 1),
            range(15, 35): slice(None, None, 5),
            range(35, 75): slice(None, None, 10),
            range(75, 101): slice(None, None, 15)
        }

        # Map of Line2D objects active in sub-plots, keyed by data UID
        self._lines = {}  # {uid: Line2D, ...}

        if title:
            self.figure.suptitle(title, y=1)
        else:
            self.figure.suptitle(flight.name, y=1)

        # create context menu
        self._pop_menu = QMenu(self)
        self._pop_menu.addAction(
            QAction('Remove', self, triggered=self._remove_patch))
        # self._pop_menu.addAction(QAction('Set Label', self,
        #     triggered=self._label_patch))
        self._pop_menu.addAction(
            QAction('Set Label', self, triggered=self._label_patch))

    def __len__(self):
        return len(self._plots)

    @property
    def axes(self):
        return [ax for ax in self._plots.values()]

    def set_plots(self, rows: int, cols=1, sharex=True, resample=False):
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
        rows : int
            Number plots to generate for display in a vertical stack
        cols : int, optional
            For now, cols will always be 1 (ignored param)
            In future would like to enable dynamic layouts with multiple
            columns as well as rows
        sharex : bool, optional
            Default True. All plots will share their X axis with each other.
        resample : bool, optional
            If true, enable dynamic resampling on each Axes, that is,
            down-sample data when zoomed completely out, and reduce the
            down-sampling as the data is viewed closer.

        Returns
        -------
        Dict[int, Axes]
            Mapping of axes index (int) to subplot (Axes) objects

        """
        self.figure.clf()
        cols = 1  # Hardcoded to 1 until future implementation
        plots = {}

        # Note: When adding subplots, the first index is 1
        for i in range(1, rows+1):
            if sharex and i > 1:
                plot = self.figure.add_subplot(rows, cols, i, sharex=plots[0])
            else:
                plot = self.figure.add_subplot(rows, cols, i)  # type: Axes
            if resample:
                plot.callbacks.connect('xlim_changed', self._xlim_resample)
            plot.callbacks.connect('ylim_changed', self._on_ylim_changed)

            plot.grid(True)
            plots[i-1] = plot

        return plots

    def _remove_patch(self):
        """PyQtSlot:
        Called by QAction menu item to remove the currently selected
        PatchGroup"""
        if self.ax_grp.active is not None:
            pg = self.ax_grp.active
            self.ax_grp.remove()
            self.line_changed.emit(
                LineUpdate(flight_id=self._flight.uid,
                           action='remove',
                           uid=pg.uid,
                           start=pg.start(), stop=pg.stop(),
                           label=None))
            self.ax_grp.deselect()
            self.draw()
        return

    def _label_patch(self):
        """PyQtSlot:
        Called by QAction menu item to add a label to the currently selected
        PatchGroup"""
        if self.ax_grp.active is not None:
            pg = self.ax_grp.active
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
        self.ax_grp.deselect()
        return

    def _xlim_resample(self, axes: Axes) -> None:
        """
        Called on change of x-limits of a given Axes. This method will
        re-sample line data in every linked Axes based on the zoom level.
        This is done for performance reasons, as with large data-sets
        interacting with the plot can become very slow.
        Re-sampling is done by slicing the data and selecting points at every
        x steps, determined by the current ratio of the plot width to
        original width.
        Ratio ranges and steps are defined in the instance _steps dictionary.

        TODO: In future user should be able to override the re-sampling step
        lookup and be able to dynamically turn off/on the resampling of data.

        """
        if self._panning:
            return
        if self._xwidth == 0:
            return

        x0, x1 = axes.get_xlim()
        ratio = int((x1 - x0) / self._xwidth * 100)
        if ratio == self._ratio:
            _log.debug("Resample ratio hasn't changed")
            return
        else:
            self._ratio = ratio

        for rs in self._steps:
            if ratio in rs:
                resample = self._steps[rs]
                break
        else:
            resample = slice(None, None, 1)

        self.resample.emit(resample.step)
        self._resample = resample

        for uid, line in self._lines.items():  # type: str, Line2D
            series = self._series.get(uid)
            sample = series[resample]
            line.set_xdata(sample.index)
            line.set_ydata(sample.values)
            line.axes.draw_artist(line)

        self.draw()

    def _on_ylim_changed(self, changed: Axes) -> None:
        if self._panning:
            self.ax_grp.rescale_patches()
        return

    def home(self, *args):
        """Autoscale Axes in the ax_grp to fit all data, then draw."""
        self.ax_grp.go_home()
        self.draw()

    def add_patch(self, start, stop, uid, label=None):
        if not self.plotted:
            self.draw()
        self.ax_grp.add_patch(0, start=start, stop=stop, uid=uid, label=label)

    def draw(self):
        super().draw()
        self.plotted = True

    # Issue #36 Enable data/channel selection and plotting
    def add_series(self, dc: types.DataChannel, axes_idx: int=0, draw=True):
        """
        Add a DataChannel (containing a pandas.Series) to the specified axes
        at axes_idx.
        If a data channel has already been plotted in the specified axes,
        we will attempt to get the Twin axes to plot the next series,
        enabling dual Y axis scales for the data.

        Parameters
        ----------
        dc : types.DataChannel
            DataChannel object to plot
        axes_idx : int
            Index of the axes objec to plot on.
        draw : bool, optional
            Optionally, set to False to defer drawing after plotting of the
            DataChannel

        """
        if len(self._lines) == 0:
            # If there are 0 plot lines we need to reset the locator/formatter
            _log.debug("Adding locator and major formatter to empty plot.")
            self.axes[0].xaxis.set_major_locator(AutoLocator())
            self.axes[0].xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))

        axes, twin = self.ax_grp.get_axes(axes_idx)

        if twin:
            color = 'orange'
        else:
            color = 'blue'

        series = dc.series()
        dc.plot(axes_idx)
        line_artist = axes.plot(series.index, series.values,
                                color=color, label=dc.label)[0]

        # Set values for x-ratio resampling
        x0, x1 = axes.get_xlim()
        width = x1 - x0
        self._xwidth = max(self._xwidth, width)

        axes.tick_params('y', colors=color)
        axes.set_ylabel(dc.label, color=color)

        self._series[dc.uid] = series  # Store reference to series for resample
        self._lines[dc.uid] = line_artist
        self.ax_grp.rescale_patches()
        if draw:
            self.figure.canvas.draw()

    def remove_series(self, dc: types.DataChannel):
        """
        Remove a line series from the plot area.
        If the channel cannot be located on any axes, None is returned

        Parameters
        ----------
        dc : types.DataChannel
            Reference of the DataChannel to remove from the plot

        Returns
        -------

        """
        if dc.uid not in self._lines:
            _log.warning("Series UID could not be located in plot_lines")
            return
        line = self._lines[dc.uid]  # type: Line2D

        axes = line.axes
        axes.lines.remove(line)
        axes.tick_params('y', colors='black')
        axes.set_ylabel('')

        self.ax_grp.rescale_patches()
        del self._lines[dc.uid]
        del self._series[dc.uid]
        dc.plot(None)

        if not len(self._lines):
            _log.warning("No Lines on any axes.")
            self.axes[0].xaxis.set_major_locator(NullLocator())
            self.axes[0].xaxis.set_major_formatter(NullFormatter())

        self.draw()

    def get_series_by_label(self, label: str):
        pass

    def onclick(self, event: MouseEvent):
        if self._zooming or self._panning:
            # Possibly hide all artists here to speed up panning
            # for line in self._lines.values():  # type: Line2D
            #     line.set_visible(False)
            return
        if not self.plotted or not len(self._lines):
            # If there is nothing plotted, don't allow user click interaction
            return
        # If the event didn't occur within an Axes, ignore it
        if event.inaxes not in self.ax_grp:
            return

        # Else, process the click event
        _log.debug("Axes Click @ xdata: {}".format(event.xdata))

        active = self.ax_grp.select(event.xdata, inner=False)

        if not active:
            _log.info("No patch at location: {}".format(event.xdata))

        if event.button == 3:
            # Right Click
            if not active:
                return
            cursor = QCursor()
            self._pop_menu.popup(cursor.pos())
            return

        elif event.button == 1:
            if active:
                # We've selected and activated an existing group
                return
            # Else: Create a new PatchGroup
            _log.info("Creating new patch group at: {}".format(event.xdata))

            try:
                pg = self.ax_grp.add_patch(event.xdata)
            except ValueError:
                _log.warning("Failed to create patch, too close to another?")
                return
            else:
                _log.info("Created new PatchGroup, uid: {}".format(pg.uid))
                self.draw()

            if self._flight.uid is not None:
                self.line_changed.emit(
                    LineUpdate(flight_id=self._flight.uid,
                               action='add',
                               uid=pg.uid,
                               start=pg.start(),
                               stop=pg.stop(),
                               label=None))
            return
        else:
            # Middle Click
            # _log.debug("Middle click is not supported.")
            return

    def onmotion(self, event: MouseEvent) -> None:
        """
        Event Handler: Pass any motion events to the AxesGroup to handle,
        as long as the user is not Panning or Zooming.

        Parameters
        ----------
        event : MouseEvent
            Matplotlib MouseEvent object with event parameters

        Returns
        -------
        None

        """
        if self._zooming or self._panning:
            return
        return self.ax_grp.onmotion(event)

    def onrelease(self, event: MouseEvent) -> None:
        """
        Event Handler: Process event and emit any changes made to the active
        Patch group (if any) upon mouse release.

        Parameters
        ----------
        event : MouseEvent
            Matplotlib MouseEvent object with event parameters

        Returns
        -------
        None

        """
        if self._zooming or self._panning:
            # for line in self._lines.values():  # type: Line2D
            #     line.set_visible(True)
            self.ax_grp.rescale_patches()
            return
        if self.ax_grp.active is not None:
            pg = self.ax_grp.active  # type: PatchGroup
            if pg.modified:
                self.line_changed.emit(
                    LineUpdate(flight_id=self._flight.uid,
                               action='modify',
                               uid=pg.uid,
                               start=pg.start(),
                               stop=pg.stop(),
                               label=pg.label))
                pg.modified = False
            self.ax_grp.deselect()
            # self.ax_grp.active = None

            self.figure.canvas.draw()

    def toggle_zoom(self):
        """Toggle plot zoom state, and disable panning state."""
        if self._panning:
            self._panning = False
        self._zooming = not self._zooming

    def toggle_pan(self):
        """Toggle plot panning state, and disable zooming state."""
        if self._zooming:
            self._zooming = False
        self._panning = not self._panning

    # EXPERIMENTAL Drag-n-Drop handlers
    # Future feature to enable dropping of Channels directly onto the plot.
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

    def get_toolbar(self, parent=None) -> QToolBar:
        """
        Get a Matplotlib Toolbar for the current plot instance, and set toolbar
        actions (pan/zoom) specific to this plot.
        We also override the home action (first by monkey-patching the
        declaration in the NavigationToolbar class) as the MPL View stack method
        provides inconsistent results with our code.

        toolbar.actions() supports indexing, with the following default
        buttons at the specified index:

            0: Home
            1: Back
            2: Forward
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

        toolbar.actions()[0].triggered.connect(self.home)
        toolbar.actions()[4].triggered.connect(self.toggle_pan)
        toolbar.actions()[5].triggered.connect(self.toggle_zoom)
        return toolbar
