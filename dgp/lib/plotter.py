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
from pandas import Series
import numpy as np

from dgp.lib.types import PlotCurve
from dgp.lib.project import Flight
from dgp.gui.dialogs import SetLineLabelDialog


class BasePlottingCanvas(FigureCanvas):
    """
    BasePlottingCanvas sets up the basic Qt Canvas parameters, and is designed
    to be subclassed for different plot types.
    """
    def __init__(self, parent=None, width=8, height=4, dpi=100):
        self.log = logging.getLogger(__name__)
        self.log.info("Initializing BasePlottingCanvas")
        self.parent = parent
        fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        super().__init__(fig)
        # FigureCanvas.__init__(self, fig)

        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self.axes = []

        self.figure.canvas.mpl_connect('button_press_event', self.onclick)
        self.figure.canvas.mpl_connect('button_release_event', self.onrelease)
        self.figure.canvas.mpl_connect('motion_notify_event', self.onmotion)
        self.figure.canvas.mpl_connect('pick_event', self.onpick)

    def generate_subplots(self, rows: int) -> None:
        """Generate vertically stacked subplots for comparing data"""
        # TODO: Experimenting with generating multiple plots, work with Chris on this class

        # Clear any current axes first
        self.axes = []
        for i in range(rows):
            if i == 0:
                sp = self.figure.add_subplot(rows, 1, i+1)  # type: Axes
            else:  # Share x-axis with plot 0
                sp = self.figure.add_subplot(rows, 1, i + 1, sharex=self.axes[0])  # type: Axes

            sp.grid(True)
            # sp.xaxis_date()
            # sp.get_xaxis().set_major_formatter(DateFormatter('%H:%M:%S'))
            sp.name = 'Axes {}'.format(i)
            # sp.callbacks.connect('xlim_changed', set_x_formatter)
            sp.callbacks.connect('ylim_changed', self._on_ylim_changed)
            self.axes.append(sp)
            i += 1

        self.compute_initial_figure()

    def add_subplot(self):
        pass

    def compute_initial_figure(self):
        pass

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

    def __len__(self):
        return len(self.axes)


ClickInfo = namedtuple('ClickInfo', ['partners', 'x0', 'width', 'xpos', 'ypos'])
LineUpdate = namedtuple('LineUpdate', ['flight_id', 'action', 'uid', 'start', 'stop', 'label'])


class LineGrabPlot(BasePlottingCanvas, QWidget):
    """
    LineGrabPlot implements BasePlottingCanvas and provides an onclick method to select flight
    line segments.
    """

    line_changed = pyqtSignal(LineUpdate)

    def __init__(self, flight, n=1, fid=None, title=None, parent=None):
        super().__init__(parent=parent)
        self.setAcceptDrops(True)
        self.log = logging.getLogger(__name__)
        self.rects = []
        self.zooming = False
        self.panning = False
        self.clicked = None  # type: ClickInfo
        self.generate_subplots(n)
        self.plotted = False
        self.timespan = datetime.timedelta(0)
        self.resample = slice(None, None, 20)
        self._lines = {}
        self._flight = flight  # type: Flight
        self._flight_id = fid

        # Issue #36
        self._plot_lines = {}  # {uid: PlotCurve, ...}

        if title:
            self.figure.suptitle(title, y=1)

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

    def update_plot(self):
        raise NotImplementedError
        flight_state = self._flight.get_plot_state()

        for channel in flight_state:
            label, axes = flight_state[channel]
            if channel not in self._plot_lines:
                pass

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
            self.line_changed.emit(LineUpdate(flight_id=self._flight_id,
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
        # self.figure.canvas.draw()
        super().draw()

    def clear(self):
        self._lines = {}
        self.rects = []
        self.resample = slice(None, None, 20)
        self.draw()
        for ax in self.axes:  # type: Axes
            for line in ax.lines[:]:
                ax.lines.remove(line)
            for patch in ax.patches[:]:
                patch.remove()
            ax.relim()
        self.draw()

    # Issue #36 Enable data/channel selection and plotting
    def add_series(self, *lines: PlotCurve, draw=True, propogate=True):
        """Add one or more data series to the specified axes as a line plot."""
        if not len(self._plot_lines):
            # If there are 0 plot lines we need to reset the major locator/formatter
            self.log.debug("Re-adding locator and major formatter to empty plot.")
            self.axes[0].xaxis.set_major_locator(AutoLocator())
            self.axes[0].xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))

        drawn_axes = {}  # Record axes that need to be redrawn
        for line in lines:
            axes = self.axes[line.axes]
            drawn_axes[line.axes] = axes
            line.line2d = axes.plot(line.data.index, line.data.values, label=line.label)[0]
            self._plot_lines[line.uid] = line
            if propogate:
                self._flight.update_series(line, action="add")

        for axes in drawn_axes.values():
            self.log.info("Adding legend, relim and autoscaling on axes: {}".format(axes))
            axes.legend()
            axes.relim()
            axes.autoscale_view()

        # self.log.info(self._plot_lines)
        if draw:
            self.figure.canvas.draw()

    def update_series(self, line: PlotCurve):
        pass

    def remove_series(self, uid):
        if uid not in self._plot_lines:
            self.log.warning("Series UID could not be located in plot_lines")
            return
        curve = self._plot_lines[uid]  # type: PlotCurve
        axes = self.axes[curve.axes]  # type: Axes
        self._flight.update_series(curve, action="remove")
        axes.lines.remove(curve.line2d)
        # axes.set
        axes.relim()
        axes.autoscale_view()
        if not axes.lines:
            axes.legend_.remove()  # Does this work? It does.
        else:
            axes.legend()
        del self._plot_lines[uid]
        if len(self._plot_lines) == 0:
            self.log.warning("No lines on plotter axes.")

        line_count = reduce(lambda acc, res: acc + res, (len(x.lines) for x in self.axes))
        if not line_count:
            self.log.warning("No Lines on any axes.")
            # This works, but then need to replace the locator when adding data back
            print(self.axes[0].xaxis.get_major_locator())
            self.axes[0].xaxis.set_major_locator(NullLocator())
            self.axes[0].xaxis.set_major_formatter(NullFormatter())

        self.figure.canvas.draw()

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
        partners = [{'uid': uid, 'rect': c_rect, 'bg': None, 'left': left, 'right': right, 'label': None}]

        for ax in self.axes:
            if ax == caxes:
                continue
            ylim = ax.get_ylim()
            height = ylim[1] - ylim[0]
            a_rect = Rectangle((xstart, ylim[0]), width, height, alpha=0.1, picker=True)
            ax.add_patch(a_rect)
            ax.draw_artist(ax.patch)
            left = num2date(a_rect.get_x())
            right = num2date(a_rect.get_x() + a_rect.get_width())
            partners.append({'uid': uid, 'rect': a_rect, 'bg': None, 'left': left,
                             'right': right, 'label': None})

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
        # TODO: What happens when a patch is added before a new plot is added?
        if not self.plotted:
            return
        lines = 0
        for ax in self.axes:
            lines += len(ax.lines)
        if lines <= 0:
            return

        if self.zooming or self.panning:  # Don't do anything when zooming/panning is enabled
            return

        # Check that the click event happened within one of the subplot axes
        if event.inaxes not in self.axes:
            return
        self.log.info("Xdata: {}".format(event.xdata))

        caxes = event.inaxes  # type: Axes
        other_axes = [ax for ax in self.axes if ax != caxes]
        # print("Current axes: {}\nOther axes obj: {}".format(repr(caxes), other_axes))

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
            # print("Width 5%: ", width)
            # Get the bottom left corner of the rectangle which will be centered at the mouse click
            x0 = event.xdata - width / 2
            y0 = ylim[0]
            height = ylim[1] - ylim[0]
            c_rect = Rectangle((x0, y0), width, height*2, alpha=0.1, picker=True)

            # Experimental replacement:
            # self.draw_patch(num2date(x0), num2date(x0+width), uid=gen_uuid('ln'))
            caxes.add_patch(c_rect)
            caxes.draw_artist(caxes.patch)

            uid = gen_uuid('ln')
            left = num2date(c_rect.get_x())
            right = num2date(c_rect.get_x() + c_rect.get_width())
            partners = [{'uid': uid, 'rect': c_rect, 'bg': None, 'left': left, 'right': right, 'label': None}]
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
                partners.append({'uid': uid, 'rect': a_rect, 'bg': None, 'left': left,
                                 'right': right, 'label': None})

            self.rects.append(partners)

            if self._flight_id is not None:
                self.line_changed.emit(LineUpdate(flight_id=self._flight_id,
                    action='add', uid=uid, start=left, stop=right, label=None))

            self.figure.canvas.draw()

            return

    def toggle_zoom(self):
        if self.panning:
            self.panning = False
        self.zooming = not self.zooming

    def toggle_pan(self):
        if self.zooming:
            self.zooming = False
        self.panning = not self.panning

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

            self._move_patch_label(attr)

            canvas = rect.figure.canvas
            axes = rect.axes
            canvas.restore_region(attr['bg'])
            axes.draw_artist(rect)
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

            if (event.xdata > left and event.xdata < left + prox):
                for p in partners:
                    p['rect'].set_edgecolor('red')
                    p['rect'].set_linewidth(3)
                event.canvas.draw()
                return 'left'

            elif (event.xdata < right and event.xdata > right - prox):
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
            label.set_animated(False)
            rect.axes.draw_artist(rect)
            attrs['bg'] = None
            # attrs['left'] = num2date(rect.get_x())
            # attrs['right'] = num2date(rect.get_x() + rect.get_width())

        uid = partners[0]['uid']
        first_rect = partners[0]['rect']
        start = num2date(first_rect.get_x())
        stop = num2date(first_rect.get_x() + first_rect.get_width())
        label = partners[0]['label']

        if self._flight_id is not None:
            self.line_changed.emit(LineUpdate(flight_id=self._flight_id,
                action='modify', uid=uid, start=start, stop=stop, label=label))

        self.clicked = None

        if self._stretching is not None:
            self._stretching = None

        self.figure.canvas.draw()

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

                    # reset label positions
                    self._move_patch_label(attr)

    def _on_xlim_changed(self, changed: Axes) -> None:
        """
        When the xlim changes (width of the graph), we want to apply a decimation algorithm to the
        dataset to speed up the visual performance of the graph. So when the graph is zoomed out
        we will plot only one in 20 data points, and as the graph is zoomed we will lower the decimation
        factor to zero.
        Parameters
        ----------
        changed

        Returns
        -------
        None
        """
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
        for ax in self.axes:
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

    def __getitem__(self, index):
        return self.axes[index]

    def __iter__(self):
        for axes in self.axes:
            yield axes

    def __len__(self):
        return len(self.axes)
