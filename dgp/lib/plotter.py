# coding: utf-8

"""
Class to handle Matplotlib plotting of data to be displayed in Qt GUI
"""

from dgp.lib.etc import gen_uuid

import logging
import datetime
from collections import namedtuple
from typing import List, Tuple
from functools import reduce

# from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QSizePolicy, QMenu, QAction, QWidget, QToolBar
from PyQt5.QtCore import pyqtSignal, QMimeData
from PyQt5.QtGui import QCursor, QDropEvent, QDragEnterEvent, QDragMoveEvent
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg as FigureCanvas,
                                                NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.dates import DateFormatter, num2date, date2num
from matplotlib.ticker import NullFormatter, NullLocator, AutoLocator
from matplotlib.backend_bases import MouseEvent, PickEvent
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import numpy as np

from dgp.lib.project import Flight
from dgp.gui.dialogs import SetLineLabelDialog
import dgp.lib.types as types


class BasePlottingCanvas(FigureCanvas):
    """
    BasePlottingCanvas sets up the basic Qt Canvas parameters, and is designed
    to be subclassed for different plot types.
    """
    def __init__(self, parent=None, width=8, height=4, dpi=100):
        self.log = logging.getLogger(__name__)
        self.log.info("Initializing BasePlottingCanvas")

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


ClickInfo = namedtuple('ClickInfo', ['partners', 'x0', 'width', 'xpos', 'ypos'])
LineUpdate = namedtuple('LineUpdate', ['flight_id', 'action', 'uid', 'start',
                                       'stop', 'label'])


class LineGrabPlot(BasePlottingCanvas, QWidget):
    """
    LineGrabPlot implements BasePlottingCanvas and provides an onclick method to
    select flight line segments.
    """

    line_changed = pyqtSignal(LineUpdate)

    def __init__(self, flight, n=1, title=None, parent=None):
        super().__init__(parent=parent)
        # Set initial sub-plot layout
        self.set_plots(rows=n)

        # Experimental
        self.setAcceptDrops(False)
        # END Experimental
        self.log = logging.getLogger(__name__)
        self.rects = []
        self.clicked = None  # type: ClickInfo
        self.plotted = False
        self.timespan = datetime.timedelta(0)
        self.resample = slice(None, None, 20)
        self._zooming = False
        self._panning = False
        self._flight = flight  # type: Flight

        self._twins = {}

        # Map of Line2D objects active in sub-plots, keyed by data UID
        self._lines = {}  # {uid: Line2D, ...}

        if title:
            self.figure.suptitle(title, y=1)
        else:
            self.figure.suptitle(flight.name, y=1)

        self._stretching = None
        self._is_near_edge = False
        self._selected_patch = None

        # create context menu
        self._pop_menu = QMenu(self)
        self._pop_menu.addAction(QAction('Remove', self,
            triggered=self._remove_patch))
        # self._pop_menu.addAction(QAction('Set Label', self,
        #     triggered=self._label_patch))
        self._pop_menu.addAction(QAction('Set Label', self,
            triggered=self._label_patch))

    @property
    def all_axes(self) -> list:
        axes = self.axes[:]
        axes.extend(self._twins.values())
        return axes

    def _remove_patch(self, partners):
        if self._selected_patch is not None:
            partners = self._selected_patch

            uid = partners[0]['uid']
            start = partners[0]['left']
            stop = partners[0]['right']

            # remove patches
            while partners:
                patch_group = partners.pop()
                patch_group['rect'].remove()
                if patch_group['label'] is not None:
                    patch_group['label'].remove()
            self.rects.remove(partners)
            self.draw()
            self.line_changed.emit(LineUpdate(flight_id=self._flight.uid,
                action='remove', uid=uid, start=start, stop=stop, label=None))
            self._selected_patch = None

    def _label_patch(self, label):
        if self._selected_patch is not None:
            partners = self._selected_patch
            current_label = partners[0]['label']
            if current_label is not None:
                dialog = SetLineLabelDialog(current_label.get_text())
            else:
                dialog = SetLineLabelDialog(None)
            if dialog.exec_():
                label = dialog.label_text
            else:
                return
        else:
            return

        for p in partners:
            rx = p['rect'].get_x()
            cx = rx + p['rect'].get_width() * 0.5
            axes = p['rect'].axes
            ylim = axes.get_ylim()
            cy = ylim[0] + abs(ylim[1] - ylim[0]) * 0.5
            axes = p['rect'].axes

            if label is not None:
                if p['label'] is not None:
                    p['label'].set_text(label)
                else:
                    p['label'] = axes.annotate(label,
                                               xy=(cx, cy),
                                               weight='bold',
                                               fontsize=6,
                                               ha='center',
                                               va='center',
                                               annotation_clip=False)
            else:
                if p['label'] is not None:
                    p['label'].remove()
                    p['label'] = None

        self.draw()

    def _move_patch_label(self, attr):
        rx = attr['rect'].get_x()
        cx = rx + attr['rect'].get_width() * 0.5
        axes = attr['rect'].axes
        ylim = axes.get_ylim()
        cy = ylim[0] + abs(ylim[1] - ylim[0]) * 0.5
        attr['label'].set_position((cx, cy))

    def draw(self):
        self.plotted = True
        super().draw()

    def clear(self):
        """Clear the canvas without resetting all of the axes properties."""
        raise NotImplementedError("Clear not properly implemented, do not use")
        self.rects = []
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

    def _set_formatters(self):
        """
        Check for lines on plot and set formatters accordingly.
        If there are no lines plotted we apply a NullLocator and NullFormatter
        If there are lines plotted or about to be plotted, re-apply an
        AutoLocator and DateFormatter.
        """
        raise NotImplementedError("Method not yet implemented")

    # Issue #36 Enable data/channel selection and plotting
    def add_series(self, dc: types.DataChannel, axes_idx: int=0, draw=True):
        """Add one or more data series to the specified axes as a line plot."""
        if len(self._lines) == 0:
            # If there are 0 plot lines we need to reset the locator/formatter
            self.log.debug("Adding locator and major formatter to empty plot.")
            self.axes[0].xaxis.set_major_locator(AutoLocator())
            self.axes[0].xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))

        axes = self[axes_idx]
        color = 'blue'

        if len(axes.lines):
            self.log.debug("Base axes already has line, getting twin")
            axes = axes.twinx()
            self._twins[axes_idx] = axes
            color = 'orange'

        series = dc.series()
        # dc.plotted = axes_idx
        dc.plot(axes_idx)
        line_artist = axes.plot(series.index, series.values,
                                color=color, label=dc.label)[0]
        axes.tick_params('y', colors=color)
        axes.set_ylabel(dc.label, color=color)

        self._lines[dc.uid] = line_artist

        # axes.legend()
        axes.relim()
        axes.autoscale_view()

        if draw:
            self.figure.canvas.draw()

    def remove_series(self, dc: types.DataChannel):

        if dc.uid not in self._lines:
            self.log.warning("Series UID could not be located in plot_lines")
            return
        line = self._lines[dc.uid]  # type: Line2D

        axes = line.axes  # due to twin axes, get from line
        axes.lines.remove(line)
        axes.tick_params('y', colors='black')
        axes.set_ylabel('')
        axes.relim()
        axes.autoscale_view()

        del self._lines[dc.uid]
        # dc.plotted = -1
        dc.plot(None)

        # line_count = reduce(lambda acc, res: acc + res,
        #                     (len(x.lines) for x in self.axes))
        if not len(self._lines):
            self.log.warning("No Lines on any axes.")
            print(self.axes[0].xaxis.get_major_locator())
            self.axes[0].xaxis.set_major_locator(NullLocator())
            self.axes[0].xaxis.set_major_formatter(NullFormatter())

        self.draw()

    def get_series_by_label(self, label: str):
        pass

    # TODO: Clean this up, allow direct passing of FlightLine Objects
    # Also convert this/test this to be used in onclick to create lines
    def draw_patch(self, start, stop, uid):
        caxes = self.axes[0]
        ylim = caxes.get_ylim()  # type: Tuple
        xstart = date2num(start)
        xstop = date2num(stop)
        width = xstop - xstart
        height = ylim[1] - ylim[0]
        c_rect = Rectangle((xstart, ylim[0]), width, height, alpha=0.2)

        caxes.add_patch(c_rect)
        caxes.draw_artist(caxes.patch)

        left = num2date(c_rect.get_x())
        right = num2date(c_rect.get_x() + c_rect.get_width())
        partners = [{'uid': uid, 'rect': c_rect, 'bg': None, 'left': left,
                     'right': right, 'label': None}]

        for ax in self.axes:
            if ax == caxes:
                continue
            ylim = ax.get_ylim()
            height = ylim[1] - ylim[0]
            a_rect = Rectangle((xstart, ylim[0]), width, height, alpha=0.1,
                               picker=True)
            ax.add_patch(a_rect)
            ax.draw_artist(ax.patch)
            left = num2date(a_rect.get_x())
            right = num2date(a_rect.get_x() + a_rect.get_width())
            partners.append({'uid': uid, 'rect': a_rect, 'bg': None,
                             'left': left, 'right': right, 'label': None})

        self.rects.append(partners)

        self.figure.canvas.draw()
        self.draw()
        return

    # Testing: Maybe way to optimize rectangle selection/dragging code
    def onpick(self, event: PickEvent):
        # Pick needs to be enabled for artist ( picker=True )
        # event.artist references the artist that triggered the pick
        self.log.debug("Picked artist: {artist}".format(artist=event.artist))

    def onclick(self, event: MouseEvent):
        # First check conditions to see if we need to handle the click.
        if not self.plotted:
            return
        # Don't do anything when zooming/panning is enabled
        if self._zooming or self._panning:
            return

        if event.inaxes not in self.all_axes:
            return

        lines = 0
        for ax in self.all_axes:
            lines += len(ax.lines)
        if lines == 0:
            return

        # Check that the click event happened within one of the subplot axes
        # if event.inaxes not in self.axes:
        #     return
        self.log.info("Xdata: {}".format(event.xdata))

        caxes = event.inaxes  # type: Axes
        other_axes = [ax for ax in self.axes if ax != caxes]

        if event.button == 3:
            # Right click
            for partners in self.rects:
                for p in partners:
                    patch = p['rect']
                    hit, _ = patch.contains(event)
                    if hit:
                        cursor = QCursor()
                        self._selected_patch = partners
                        self._pop_menu.popup(cursor.pos())
            return

        else:
            # Left click
            for partners in self.rects:
                patch = partners[0]['rect']
                if patch.get_x() <= event.xdata <= patch.get_x() + patch.get_width():
                    # Then we clicked an existing rectangle
                    x0, _ = patch.xy
                    width = patch.get_width()
                    self.clicked = ClickInfo(partners, x0, width, event.xdata, event.ydata)
                    self._stretching = self._is_near_edge

                    for attrs in partners:
                        rect = attrs['rect']
                        rect.set_animated(True)
                        label = attrs['label']
                        if label is not None:
                            label.set_animated(True)
                        r_canvas = rect.figure.canvas
                        r_axes = rect.axes  # type: Axes
                        r_canvas.draw()
                        attrs['bg'] = r_canvas.copy_from_bbox(r_axes.bbox)
                    return

            # else: Create a new rectangle on all axes
            # TODO: Use the new draw_patch function to do this (some modifications required)
            ylim = caxes.get_ylim()  # type: Tuple
            xlim = caxes.get_xlim()  # type: Tuple
            width = (xlim[1] - xlim[0]) * np.float64(0.05)
            # Get the bottom left corner of the rectangle which will be centered at the mouse click
            x0 = event.xdata - width / 2
            y0 = ylim[0]
            height = ylim[1] - ylim[0]
            c_rect = Rectangle((x0, y0), width, height*2, alpha=0.1, picker=True)

            # Experimental replacement:
            caxes.add_patch(c_rect)
            caxes.draw_artist(caxes.patch)

            uid = gen_uuid('ln')
            left = num2date(c_rect.get_x())
            right = num2date(c_rect.get_x() + c_rect.get_width())
            partners = [{'uid': uid, 'rect': c_rect, 'bg': None, 'left': left,
                         'right': right, 'label': None}]
            for ax in other_axes:
                x0 = event.xdata - width / 2
                ylim = ax.get_ylim()
                y0 = ylim[0]
                height = ylim[1] - ylim[0]
                a_rect = Rectangle((x0, y0), width, height * 2, alpha=0.1)
                ax.add_patch(a_rect)
                ax.draw_artist(ax.patch)
                left = num2date(a_rect.get_x())
                right = num2date(a_rect.get_x() + a_rect.get_width())
                partners.append({'uid': uid, 'rect': a_rect, 'bg': None,
                                 'left': left, 'right': right, 'label': None})

            self.rects.append(partners)

            if self._flight.uid is not None:
                self.line_changed.emit(
                    LineUpdate(flight_id=self._flight.uid, action='add',
                               uid=uid, start=left, stop=right, label=None))

            self.figure.canvas.draw()
            return

    def toggle_zoom(self):
        if self._panning:
            self._panning = False
        self._zooming = not self._zooming

    def toggle_pan(self):
        if self._zooming:
            self._zooming = False
        self._panning = not self._panning

    def _move_rect(self, event):
        partners, x0, width, xclick, yclick = self.clicked

        dx = event.xdata - xclick
        for attr in partners:
            rect = attr['rect']
            label = attr['label']
            if self._stretching is not None:
                if self._stretching == 'left':
                    if width - dx > 0:
                        rect.set_x(x0 + dx)
                        rect.set_width(width - dx)
                elif self._stretching == 'right':
                    if width + dx > 0:
                        rect.set_width(width + dx)
            else:
                rect.set_x(x0 + dx)

            if attr['label'] is not None:
                self._move_patch_label(attr)

            canvas = rect.figure.canvas
            axes = rect.axes
            canvas.restore_region(attr['bg'])
            axes.draw_artist(rect)
            if attr['label'] is not None:
                axes.draw_artist(label)
            canvas.blit(axes.bbox)

    def _near_edge(self, event, prox=0.0005):
        for partners in self.rects:
            attr = partners[0]
            rect = attr['rect']

            axes = rect.axes
            canvas = rect.figure.canvas

            left = rect.get_x()
            right = left + rect.get_width()

            # if (event.xdata > left and event.xdata < left + prox):
            if left < event.xdata < left + prox:
                for p in partners:
                    p['rect'].set_edgecolor('red')
                    p['rect'].set_linewidth(3)
                event.canvas.draw()
                return 'left'

            # elif (event.xdata < right and event.xdata > right - prox):
            elif right - prox < event.xdata < right:
                for p in partners:
                    p['rect'].set_edgecolor('red')
                    p['rect'].set_linewidth(3)
                event.canvas.draw()
                return 'right'

            else:
                if rect.get_linewidth() != 1.0 and self._stretching is None:
                    for p in partners:
                        p['rect'].set_edgecolor(None)
                        p['rect'].set_linewidth(None)
                    event.canvas.draw()

        return None

    def onmotion(self, event: MouseEvent):
        if event.inaxes not in self.axes:
            return

        if self.clicked is not None:
            self._move_rect(event)
        else:
            self._is_near_edge = self._near_edge(event)

    def onrelease(self, event: MouseEvent):

        if self.clicked is None:
            if self._selected_patch is not None:
                self._selected_patch = None
            return  # Nothing Selected

        partners = self.clicked.partners
        for attrs in partners:
            rect = attrs['rect']
            rect.set_animated(False)
            label = attrs['label']
            if label is not None:
                label.set_animated(False)
            rect.axes.draw_artist(rect)
            attrs['bg'] = None

        uid = partners[0]['uid']
        first_rect = partners[0]['rect']
        start = num2date(first_rect.get_x())
        stop = num2date(first_rect.get_x() + first_rect.get_width())
        label = partners[0]['label']

        if self._flight.uid is not None:
            self.line_changed.emit(LineUpdate(flight_id=self._flight.uid,
                action='modify', uid=uid, start=start, stop=stop, label=label))

        self.clicked = None

        if self._stretching is not None:
            self._stretching = None

        self.figure.canvas.draw()

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
    # END EXPERIMENT

    @staticmethod
    def get_time_delta(x0, x1):
        """Return a time delta from a plot axis limit"""
        return num2date(x1) - num2date(x0)

    def _on_ylim_changed(self, changed: Axes):
        for partners in self.rects:
            for attr in partners:
                if attr['rect'].axes == changed:
                    # reset rectangle sizes
                    ylim = changed.get_ylim()
                    attr['rect'].set_y(ylim[0])
                    attr['rect'].set_height(abs(ylim[1] - ylim[0]))

                    if attr['label'] is not None:
                        # reset label positions
                        self._move_patch_label(attr)

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
        self.log.info("XLIM Changed!")
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
                    self.log.debug("Resampling to: {}".format(self.resample))
            ax.relim()
            ax.get_xaxis().set_major_formatter(DateFormatter('%H:%M:%S'))
        self.figure.canvas.draw()

    def get_toolbar(self, parent=None) -> QToolBar:
        """
        Get a Matplotlib Toolbar for the current plot instance, and set toolbar actions (pan/zoom) specific to this plot
        toolbar.actions() supports indexing, with the following default buttons at the specified index:
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
        [parent]
            Optional Qt Parent for this object

        Returns
        -------
        QtWidgets.QToolBar : Matplotlib Qt Toolbar used to control this plot instance
        """
        toolbar = NavigationToolbar(self, parent=parent)
        toolbar.actions()[4].triggered.connect(self.toggle_pan)
        toolbar.actions()[5].triggered.connect(self.toggle_zoom)
        return toolbar

