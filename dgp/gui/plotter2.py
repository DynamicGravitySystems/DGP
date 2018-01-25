# coding: utf-8

# PROTOTYPE new LineGrabPlot class based on mplutils utility classes
import logging

import matplotlib as mpl
from PyQt5.QtWidgets import QSizePolicy, QMenu, QAction, QWidget, QToolBar
from PyQt5.QtCore import pyqtSignal, QMimeData
from PyQt5.QtGui import QCursor, QDropEvent, QDragEnterEvent, QDragMoveEvent
import PyQt5.QtCore as QtCore
import PyQt5.QtWidgets as QtWidgets
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT)
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

from ..lib.types import DataChannel, LineUpdate
from .mplutils import *


_log = logging.getLogger(__name__)

#######
# WIP #
#######


"""Design Requirements of FlightLinePlot:

Use Case:
FlightLinePlot (FLP) is designed for a specific use case, where the user may 
plot raw Gravity and GPS data channels on a synchronized x-axis plot in order to 
select distinct 'lines' of data (where the Ship or Aircraft has turned to 
another heading).

Requirements:
 - Able to display 2-4 plots displayed in a row with a linked x-axis scale.
 - Each plot must have dual y-axis scales and should limit the number of lines 
plotted to 1 per y-axis to allow for plotting of different channels of widely 
varying amplitudes.
- User can enable a 'line selection mode' which allows the user to 
graphically specify flight lines through the following functionality:
 - On click, a new semi-transparent rectangle 'patch' is created across all 
 visible axes. If there is no patch in the area already.
 - On drag of a patch, it should follow the mouse, allowing the user to 
 adjust its position.
 - On click and drag of the edge of any patch it should resize to the extent 
 of the movement, allowing the user to resize the patches.
 - On right-click of a patch, a context menu should be displayed allowing 
 user to label, or delete, or specify precise (spinbox) x/y limits of the patch

"""

__all__ = ['FlightLinePlot']


class BasePlottingCanvas(FigureCanvas):
    """
    BasePlottingCanvas sets up the basic Qt FigureCanvas parameters, and is
    designed to be subclassed for different plot types.
    Mouse events are connected to the canvas here, and the handlers should be
    overriden in sub-classes to provide custom actions.
    """
    def __init__(self, parent=None, width=8, height=4, dpi=100):
        super().__init__(Figure(figsize=(width, height), dpi=dpi,
                                tight_layout=True))

        self.setParent(parent)
        super().setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        super().updateGeometry()

        self.figure.canvas.mpl_connect('pick_event', self.onpick)
        self.figure.canvas.mpl_connect('button_press_event', self.onclick)
        self.figure.canvas.mpl_connect('button_release_event', self.onrelease)
        self.figure.canvas.mpl_connect('motion_notify_event', self.onmotion)

    def onclick(self, event: MouseEvent):
        pass

    def onrelease(self, event: MouseEvent):
        pass

    def onmotion(self, event: MouseEvent):
        pass

    def onpick(self, event: PickEvent):
        pass


class FlightLinePlot(BasePlottingCanvas):
    linechanged = pyqtSignal(LineUpdate)

    def __init__(self, flight, rows=3, width=8, height=4, dpi=100,
                 parent=None, **kwargs):
        _log.debug("Initializing FlightLinePlot")
        super().__init__(parent=parent, width=width, height=height, dpi=dpi)

        self._flight = flight
        self.mgr = kwargs.get('axes_mgr', None) or StackedAxesManager(
            self.figure, rows=rows)
        self.pm = kwargs.get('patch_mgr', None) or PatchManager(parent=parent)

        self._home_action = QAction("Home")
        self._home_action.triggered.connect(lambda *args: print("Home Clicked"))
        self._zooming = False
        self._panning = False
        self._grab_lines = False
        self._toolbar = None

    def set_mode(self, grab=True):
        self._grab_lines = grab

    def get_toolbar(self, home_callback=None):
        """Configure and return the Matplotlib Toolbar used to interactively
        control the plot area.
        Here we replace the default MPL Home action with a custom action,
        and attach additional callbacks to the Pan and Zoom buttons.
        """
        if self._toolbar is not None:
            return self._toolbar

        def toggle(action):
            if action.lower() == 'zoom':
                print("Toggling zoom")
                self._panning = False
                self._zooming = not self._zooming
            elif action.lower() == 'pan':
                print("Toggling Pan")
                self._zooming = False
                self._panning = not self._panning
            else:
                self._zooming = False
                self._panning = False

        tb = NavigationToolbar2QT(self, parent=None)
        _home = tb.actions()[0]

        new_home = QAction(_home.icon(), "Home", parent=tb)
        home_callback = home_callback or (lambda *args: None)
        new_home.triggered.connect(home_callback)
        new_home.setToolTip("Reset View")
        tb.insertAction(_home, new_home)
        tb.removeAction(_home)

        tb.actions()[4].triggered.connect(lambda x: toggle('pan'))
        tb.actions()[5].triggered.connect(lambda x: toggle('zoom'))
        self._toolbar = tb
        return tb

    def add_series(self, channel: DataChannel, row=0, draw=True):
        self.mgr.add_series(channel.series(), row=row, uid=channel.uid)

    def onclick(self, event: MouseEvent):
        if not self._grab_lines or self._zooming or self._panning:
            print("Not in correct mode")
            return
        # If the event didn't occur within an Axes, ignore it
        if event.inaxes not in self.mgr:
            return

        # Else, process the click event
        # Get the patch group at click loc if it exists
        active = self.pm.select(event.xdata, inner=False)
        print("Active group: ", active)

        # Right Button
        if event.button == 3 and active:
            cursor = QCursor()
            self._pop_menu.popup(cursor.pos())
            return

        # Left Button
        elif event.button == 1 and not active:
            print("Creating new patch group")
            patches = []
            for ax, twin in self.mgr:
                xmin, xmax = ax.get_xlim()
                width = (xmax - xmin) * 0.05
                x0 = event.xdata - width / 2
                y0, y1 = ax.get_ylim()
                rect = Rectangle((x0, y0), width, height=1, alpha=0.1,
                                 edgecolor='black', linewidth=2, picker=True)
                patch = ax.add_patch(rect)
                patch.set_picker(True)
                ax.draw_artist(patch)
                patches.append(patch)
            pg = RectanglePatchGroup(*patches)
            self.pm.add_group(pg)
            self.draw()

            if self._flight.uid is not None:
                self.linechanged.emit(
                    LineUpdate(flight_id=self._flight.uid,
                               action='add',
                               uid=pg.uid,
                               start=pg.start(),
                               stop=pg.stop(),
                               label=None))
            return
        # Middle Button/Misc Button
        else:
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
        self.pm.onmotion(event)

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
            self.pm.rescale_patches()
            self.draw()
            return

        active = self.pm.active
        if active is not None:
            if active.modified:
                self.linechanged.emit(
                    LineUpdate(flight_id=self._flight.uid,
                               action='modify',
                               uid=active.uid,
                               start=active.start(),
                               stop=active.stop(),
                               label=active.label))
            self.pm.deselect()
            self.figure.canvas.draw()
