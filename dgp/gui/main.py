# coding: utf-8

import os
import pathlib
import functools
import logging
from typing import Dict, Union

from pandas import Series, DataFrame
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QListWidgetItem
from PyQt5.QtCore import pyqtSignal, pyqtBoundSignal, Qt
from PyQt5.QtGui import QColor, QStandardItemModel, QStandardItem, QIcon
from PyQt5.uic import loadUiType

import dgp.lib.project as prj
from dgp.gui.loader import LoadFile
from dgp.lib.plotter import LineGrabPlot, LineUpdate
from dgp.lib.types import PlotLine
from dgp.lib.etc import gen_uuid
from dgp.gui.utils import ConsoleHandler, LOG_FORMAT, LOG_LEVEL_MAP, get_project_file
from dgp.gui.dialogs import ImportData, AddFlight, CreateProject, InfoDialog, AdvancedImport
from dgp.gui.models import TableModel, ProjectModel, ProjectItem

from dgp.gui.widgets import DropTarget

# Load .ui form
main_window, _ = loadUiType('dgp/gui/ui/main_window.ui')


def autosave(method):
    """Decorator to call save_project for functions that alter project state."""
    def enclosed(self, *args, **kwargs):
        if kwargs:
            result = method(self, *args, **kwargs)
        elif len(args) > 1:
            result = method(self, *args)
        else:
            result = method(self)
        self.save_project()
        return result
    return enclosed


class MainWindow(QtWidgets.QMainWindow, main_window):
    """An instance of the Main Program Window"""

    # Define signals to allow updating of loading progress
    status = pyqtSignal(str)  # type: pyqtBoundSignal
    progress = pyqtSignal(int)  # type: pyqtBoundSignal

    def __init__(self, project: Union[prj.GravityProject, prj.AirborneProject]=None, *args):
        super().__init__(*args)

        self.setupUi(self)  # Set up ui within this class - which is base_class defined by .ui file
        self.title = 'Dynamic Gravity Processor'

        # Setup logging
        self.log = logging.getLogger(__name__)
        console_handler = ConsoleHandler(self.write_console)
        console_handler.setFormatter(LOG_FORMAT)
        self.log.addHandler(console_handler)
        self.log.setLevel(logging.DEBUG)

        # Setup Project
        self.project = project
        # Experimental: use the _model to affect changes to the project.
        self._model = ProjectModel(project)

        # See http://doc.qt.io/qt-5/stylesheet-examples.html#customizing-qtreeview
        # Set Stylesheet customizations for GUI Window
        self.setStyleSheet("""
            QTreeView::item {

            }
            QTreeView::branch:has-siblings:adjoins-them {
                /*border: 1px solid black; */
            }
            QTreeView::branch {
                background: palette(base);
            }

            QTreeView::branch:has-siblings:!adjoins-item {
                /*background: cyan;*/
            }

            QTreeView::branch:has-siblings:adjoins-item {
                background: orange;
            }

            QTreeView::branch:!has-children:!has-siblings:adjoins-item {
                background: blue;
            }

            QTreeView::branch:closed:has-children:has-siblings {
                background: none;
                image: url(:/images/assets/branch-closed.png);
            }

            QTreeView::branch:has-children:!has-siblings:closed {
                image: url(:/images/assets/branch-closed.png);
            }

            QTreeView::branch:open:has-children:has-siblings {
                background: none;
                image: url(:/images/assets/branch-open.png);
            }

            QTreeView::branch:open:has-children:!has-siblings {
                image: url(:/images/assets/branch-open.png);
            }
        """)

        # Initialize plotter canvas
        self.gravity_stack = QtWidgets.QStackedWidget()
        self.gravity_plot_layout.addWidget(self.gravity_stack)
        self.gps_stack = QtWidgets.QStackedWidget()
        self.gps_plot_layout.addWidget(self.gps_stack)

        # Initialize Variables
        self.import_base_path = pathlib.Path('../tests').resolve()

        self.current_flight = None  # type: prj.Flight
        self.current_flight_index = QtCore.QModelIndex()  # type: QtCore.QModelIndex
        self.tree_index = None  # type: QtCore.QModelIndex
        self.flight_plots = {}  # Stores plotter objects for flights

        self.project_tree = ProjectTreeView(parent=self, project=self.project)
        self.project_tree.setMinimumWidth(300)
        self.project_dock_grid.addWidget(self.project_tree, 0, 0, 1, 2)

        # Issue #36 Channel Selection Model
        self.std_model = None  # type: QStandardItemModel

    def load(self):
        self._init_plots()
        self._init_slots()
        # self.update_project(signal_flight=True)
        # self.project_tree.refresh()
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.save_project()
        self.show()
        try:
            self.progress.disconnect()
            self.status.disconnect()
        except TypeError:  # This will happen if there are no slots connected
            pass

    def _init_plots(self) -> None:
        # TODO: The logic here and in add_flight_dialog needs to be consolidated into single function
        # TODO: If a flight has saved data channel selection plot those instead of the default
        """
        Initialize plots for flight objects in project.
        This allows us to switch between individual plots without re-plotting giving a vast
        performance increase.
        Returns
        -------
        None
        """
        self.progress.emit(0)
        for i, flight in enumerate(self.project.flights):  # type: int, prj.Flight
            if flight.uid in self.flight_plots:
                continue

            plot, widget = self._new_plot_widget(flight, rows=3)
            plot.series_changed.connect(flight.update_series)

            self.flight_plots[flight.uid] = plot, widget
            self.gravity_stack.addWidget(widget)
            # gravity = flight.gravity
            self.log.debug("Plotting using plot_flight_main method")
            self.plot_defaults(plot, flight)

            # TODO: Need to disconnect these at some point?
            # Don't connect this until after self.plot_flight_main or it will trigger on initial draw
            plot.line_changed.connect(self._on_modified_line)
            self.log.debug("Initialized Flight Plot: {}".format(plot))
            self.status.emit('Flight Plot {} Initialized'.format(flight.name))
            self.progress.emit(i+1)

    def _on_modified_line(self, info):
        for flight in self.project.flights:
            if info.flight_id == flight.uid:

                if info.uid in flight.lines:
                    if info.action == 'modify':
                        line = flight.lines[info.uid]
                        line.start = info.start
                        line.stop = info.stop
                        line.label = info.label
                        self.log.debug("Modified line: start={start}, "
                                       "stop={stop}, label={label}"
                                       .format(start=info.start,
                                               stop=info.stop,
                                               label=info.label))
                    elif info.action == 'remove':
                        flight.remove_line(info.uid)
                        self.log.debug("Removed line: start={start}, "
                                       "stop={stop}, label={label}"
                                       .format(start=info.start,
                                               stop=info.stop,
                                               label=info.label))
                else:
                    flight.add_line(info.start, info.stop, uid=info.uid)
                    self.log.debug("Added line to flight {flt}: start={start}, stop={stop}, "
                                   "label={label}"
                                   .format(flt=flight.name,
                                           start=info.start,
                                           stop=info.stop,
                                           label=info.label))

    @staticmethod
    def _new_plot_widget(flight, rows=2):
        plot = LineGrabPlot(rows, fid=flight.uid, title=flight.name)
        plot_toolbar = plot.get_toolbar()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(plot)
        layout.addWidget(plot_toolbar)

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)

        return plot, widget

    def _init_slots(self):
        """Initialize PyQt Signals/Slots for UI Buttons and Menus"""

        # File Menu Actions #
        self.action_exit.triggered.connect(self.exit)
        self.action_file_new.triggered.connect(self.new_project_dialog)
        self.action_file_open.triggered.connect(self.open_project_dialog)
        self.action_file_save.triggered.connect(self.save_project)

        # Project Menu Actions #
        self.action_import_data.triggered.connect(self.import_data_dialog)
        self.action_add_flight.triggered.connect(self.add_flight_dialog)

        # Project Tree View Actions #
        # self.prj_tree.doubleClicked.connect(self.log_tree)
        self.project_tree.clicked.connect(self.flight_changed)

        # Project Control Buttons #
        self.prj_add_flight.clicked.connect(self.add_flight_dialog)
        self.prj_import_data.clicked.connect(self.import_data_dialog)

        # Channel Panel Buttons #
        # self.selectAllChannels.clicked.connect(self.set_channel_state)

        # self.gravity_channels.itemChanged.connect(self.channel_changed)
        # self.resample_value.valueChanged[int].connect(self.resample_rate_changed)

        # Console Window Actions #
        self.combo_console_verbosity.currentIndexChanged[str].connect(self.set_logging_level)

        # Testing #
        self.populate_channels(None)

    # Experimental: Issue #36 Channel Selection
    def populate_channels(self, flight: prj.Flight):
        # TODO: Allow reset of entire list, or specific headers (via context menu right-click)
        if flight is None:
            return
        std_model = QStandardItemModel()
        header_flags = Qt.NoItemFlags
        std_header = QStandardItem("Data Channels")
        std_header.setFlags(header_flags)
        std_model.appendRow(std_header)

        drag_flags = Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsEnabled

        channels = []
        if flight.gravity is not None:
            channels += list(flight.gravity.keys())

        if flight.gps is not None:
            channels += list(flight.gps.keys())

        # TODO: Maybe create private function to setup channel items
        for channel in channels:
            print(channel)
            if channel.lower() in flight.get_plotted_lines():
                continue
            drag_item = QStandardItem(channel)
            drag_item.setData(channel, Qt.UserRole)
            drag_item.setFlags(drag_flags)
            std_model.appendRow(drag_item)

        # Track header keys for plot instances
        plot_headers = []
        # flight_plots format: {flt_uid: (plot, stack_widget)}
        for ax in range(len(self.flight_plots[flight.uid][0])):
            ax_name = "Plot: {}".format(ax)
            plot_headers.append(ax_name)
            ax_header = QStandardItem(ax_name)
            ax_header.setData(ax, role=Qt.UserRole)
            ax_header.setFlags(header_flags)
            std_model.appendRow(ax_header)
            # Populate already plotted channels beneath their respective header
            plotted_channels = flight.get_plotted_lines(ax)
            for channel in plotted_channels:
                drag_item = QStandardItem(channel)
                drag_item.setData(channel, Qt.UserRole)
                drag_item.setFlags(drag_flags)
                std_model.appendRow(drag_item)

        std_model.itemChanged.connect(self.channel_changed)
        self.list_channels.setModel(std_model)

    def channel_changed(self, item: QStandardItem):
        headers = ["Data Channels"]
        for ax in range(len(self.flight_plots[self.current_flight.uid][0])):
            headers.append("Plot: {}".format(ax))

        model = self.list_channels.model()
        row = model.indexFromItem(item).row()
        axes_index = None
        for i in reversed(range(row)):
            inspect = model.item(i)
            if inspect.text() in headers:
                axes_index = inspect.data(Qt.UserRole)
                self.log.debug("Item {} parent: {}".format(item.text(), inspect.text()))
                break

        plot = self.flight_plots[self.current_flight.uid][0]  # type: LineGrabPlot
        if axes_index is None:
            # TODO: Implement action upon removal of series from plot
            # Remove
            # plot.remove_series('')
            return
        channel = item.data(Qt.UserRole)
        linedata = self.current_flight.gravity[channel]
        line = PlotLine(linedata, channel, 'Purple', gen_uuid('line'))
        plot.add_series(line, ax_index=axes_index)

    def exit(self):
        """PyQt Slot: Exit the PyQt application by closing the main window (self)"""
        self.close()

    # Experimental Context Menu
    def create_actions(self):
        info_action = QtWidgets.QAction('&Info')
        info_action.triggered.connect(self.flight_info)
        return [info_action]

    def flight_info(self):
        self.log.info("Printing info about the selected flight: {}".format(self.current_flight))

    def set_logging_level(self, name: str):
        """PyQt Slot: Changes logging level to passed string logging level name."""
        self.log.debug("Changing logging level to: {}".format(name))
        level = LOG_LEVEL_MAP[name.lower()]
        self.log.setLevel(level)

    def write_console(self, text, level):
        """PyQt Slot: Logs a message to the GUI console"""
        log_color = {'DEBUG': QColor('DarkBlue'), 'INFO': QColor('Green'), 'WARNING': QColor('Red'),
                     'ERROR': QColor('Pink'), 'CRITICAL': QColor(
                'Orange')}.get(level.upper(), QColor('Black'))

        self.text_console.setTextColor(log_color)
        self.text_console.append(str(text))
        self.text_console.verticalScrollBar().setValue(self.text_console.verticalScrollBar().maximum())

    #####
    # Plot functions
    #####

    def flight_changed(self, index: QtCore.QModelIndex) -> None:
        """
        PyQt Slot called upon change in flight selection using the Project Tree View.
        When a new flight is selected we want to plot the gravity channel in subplot 0, with cross and long in subplot 1
        GPS data will be plotted in the GPS tab on its own plot.

        Logic:
        If item @ index is not a Flight object Then return
        If current_flight == item.data() @ index, Then return


        Parameters
        ----------
        index : QtCore.QModelIndex
            Model index referencing the newly selected TreeView Item

        Returns
        -------
        None

        """
        self.tree_index = index
        # qitem = self.project_tree.model().itemFromIndex(index)  # type: QtGui.QStandardItem
        qitem = index.internalPointer()
        if qitem is None:
            return
        qitem_data = qitem.data(QtCore.Qt.UserRole)

        if not isinstance(qitem_data, prj.Flight):
            # Return as we're not interested in handling non-flight selections
            return None
        else:
            flight = qitem_data  # type: prj.Flight

        if self.current_flight == flight:
            # Return as this is the same flight as previously selected
            return None
        else:
            self.current_flight = flight

        # Write flight information to TextEdit box in GUI
        self.text_info.clear()
        self.text_info.appendPlainText(str(flight))

        # Check if there is a plot for this flight already
        if self.flight_plots.get(flight.uid, None) is not None:
            grav_plot, stack_widget = self.flight_plots[flight.uid]  # type: LineGrabPlot
            self.log.info("Switching widget stack")
            self.gravity_stack.setCurrentWidget(stack_widget)
        else:
            self.log.error("No plot for this flight found.")
            return

        self.populate_channels(flight)

        if not grav_plot.plotted:
            self.plot_defaults(grav_plot, flight)
        return

    def redraw(self, flt_id: str) -> None:
        """
        Redraw the main flight plot (gravity, cross/long, eotvos) for the specific flight.

        Parameters
        ----------
        flt_id : str
            Flight uuid of flight to replot.

        Returns
        -------
        None
        """
        self.log.warning("Redrawing plot")
        plot, _ = self.flight_plots[flt_id]
        flt = self.project.get_flight(flt_id)  # type: prj.Flight
        self.plot_defaults(plot, flt)

    def plot_defaults(self, plot: LineGrabPlot, flight: prj.Flight) -> None:
        """
        Plot a flight on the main plot area as a time series, displaying gravity, long/cross and eotvos
        By default, expects a plot with 3 subplots accesible via getattr notation.
        Gravity channel will be plotted on subplot 0
        Long and Cross channels will be plotted on subplot 1
        Eotvos Correction channel will be plotted on subplot 2
        After plotting, call the plot.draw() to set plot.plotted to true, and draw the figure.

        Parameters
        ----------
        plot : LineGrabPlot
            LineGrabPlot object used to draw the plot on
        flight : prj.Flight
            Flight object with related Gravity and GPS properties to plot

        Returns
        -------
        None
        """
        plot.clear()
        queue_draw = False
        grav_series = flight.gravity
        eotvos_series = flight.eotvos
        if grav_series is not None:
            # Issue #36
            # TODO: How to save and reference these lines for modification later
            grav_line = PlotLine(grav_series['gravity'], 'Gravity', 'blue', gen_uuid('line'))
            cross_line = PlotLine(grav_series['cross'], 'Cross', 'green', gen_uuid('line'))
            long_line = PlotLine(grav_series['long'], 'Long', 'red', gen_uuid('line'))
            plot.add_series(grav_line)
            plot.add_series(cross_line, long_line, ax_index=1)
        if eotvos_series is not None:
            eot_line = PlotLine(eotvos_series['eotvos'], 'Eotvos', 'black', gen_uuid('line'))
            plot.add_series(eot_line, ax_index=2)
        for line in flight.lines:
            plot.draw_patch(line.start, line.stop, line.uid)
            queue_draw = True
        if queue_draw:
            plot.draw()

    @staticmethod
    def plot_time_series(plot: LineGrabPlot, data: DataFrame, fields: Dict):
        # Currently unused
        plot.clear()
        for index in fields:
            if isinstance(fields[index], str):
                series = data.get(fields[index])  # type: Series
                plot.plot_series(plot[index], series)
                continue
            for field in fields[index]:
                series = data.get(field)  # type: Series
                plot.plot_series(plot[index], series)
        plot.draw()
        plot.plotted = True

    def progress_dialog(self, title, min=0, max=1):
        dialog = QtWidgets.QProgressDialog(title, "Cancel", min, max, self)
        dialog.setWindowTitle("Loading...")
        dialog.setModal(True)
        dialog.setMinimumDuration(0)
        dialog.setCancelButton(None)
        dialog.setValue(0)
        return dialog

    def import_data(self, path: pathlib.Path, dtype: str, flight: prj.Flight, fields=None):
        self.log.info("Importing <{dtype}> from: Path({path}) into <Flight({name})>".format(dtype=dtype, path=str(path),
                                                                                            name=flight.name))
        if path is None:
            return False
        loader = LoadFile(path, dtype, flight.uid, fields=fields, parent=self)

        # Curry functions to execute on thread completion.
        add_data = functools.partial(self.project.add_data, flight_uid=flight.uid)
        # tree_refresh = functools.partial(self.project_tree.refresh, curr_flightid=flight.uid)
        redraw_flt = functools.partial(self.redraw, flight.uid)
        prog = self.progress_dialog("Loading", 0, 0)

        loader.data.connect(add_data)
        loader.progress.connect(prog.setValue)
        # loader.loaded.connect(tree_refresh)
        loader.loaded.connect(redraw_flt)
        loader.loaded.connect(self.save_project)
        loader.loaded.connect(prog.close)
        loader.start()

    #####
    # Project dialog functions
    #####

    def import_data_dialog(self) -> None:
        """Load data file (GPS or Gravity) using a background Thread, then hand
        it off to the project."""
        dialog = AdvancedImport(self.project, self.current_flight)
        if dialog.exec_():
            path, dtype, fields, flight = dialog.content
            # print("path: {}  type: {}\nfields: {}\nflight: {}".format(path, dtype, fields, flight))
            self.import_data(path, dtype, flight, fields=fields)
            return

        return
        # Old dialog:
        dialog = ImportData(self.project, self.current_flight)
        if dialog.exec_():
            path, dtype, flt_id = dialog.content
            flight = self.project.get_flight(flt_id)
            # plot, _ = self.flight_plots[flt_id]
            # plot.plotted = False
            self.log.info("Importing {} file from {} into flight: {}".format(dtype, path, flight.uid))
            self.import_data(path, dtype, flight)

    def new_project_dialog(self) -> QtWidgets.QMainWindow:
        new_window = True
        dialog = CreateProject()
        if dialog.exec_():
            self.log.info("Creating new project")
            project = dialog.project
            if new_window:
                self.log.debug("Opening project in new window")
                return MainWindow(project)
            else:
                self.project = project
                self.project.save()
                self.update_project()

    # TODO: This will eventually require a dialog to allow selection of project type, or
    # a metadata file in the project directory specifying type info
    def open_project_dialog(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Open Project Directory", os.path.abspath('..'))
        if not path:
            return

        prj_file = get_project_file(path)
        if prj_file is None:
            self.log.warning("No project file's found in directory: {}".format(path))
            return
        self.save_project()
        self.project = prj.AirborneProject.load(prj_file)
        self.update_project()
        return

    @autosave
    def add_flight_dialog(self) -> None:
        dialog = AddFlight(self.project)
        if dialog.exec_():
            self.log.info("Adding flight:")
            flight = dialog.flight
            self.project.add_flight(flight)

            if dialog.gravity:
                self.import_data(dialog.gravity, 'gravity', flight)
            if dialog.gps:
                self.import_data(dialog.gps, 'gps', flight)

            plot, widget = self._new_plot_widget(flight, rows=3)
            plot.line_changed.connect(self._on_modified_line)
            self.gravity_stack.addWidget(widget)
            self.flight_plots[flight.uid] = plot, widget
            plot.series_changed.connect(flight.update_series)
            return

    def save_project(self) -> None:
        if self.project is None:
            return
        if self.project.save():
            self.setWindowTitle(self.title + ' - {} [*]'.format(self.project.name))
            self.setWindowModified(False)
            self.log.info("Project saved.")
        else:
            self.log.info("Error saving project.")


class ProjectTreeView(QtWidgets.QTreeView):
    def __init__(self, project=None, parent=None):
        super().__init__(parent=parent)

        self._project = project
        # Dict indexes to store [flight_uid] = QItemIndex
        self._indexes = {}
        self.log = logging.getLogger(__name__)

        self.setMinimumSize(QtCore.QSize(0, 300))
        self.setAlternatingRowColors(True)
        self.setAutoExpandDelay(1)
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)
        # self.setHeaderHidden(True)
        self.setObjectName('project_tree')
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self._init_model()

    def _init_model(self):
        """Initialize a new-style ProjectModel from models.py"""
        model = ProjectModel(self._project)
        model.rowsAboutToBeInserted.connect(self.begin_insert)
        model.rowsInserted.connect(self.end_insert)
        self.setModel(model)
        self.expandAll()

    def begin_insert(self, index, start, end):
        print("Inserting rows: {}, {}".format(start, end))

    def end_insert(self, index, start, end):
        print("Finixhed inserting rows, running update")
        # index is parent index
        model = self.model()
        uindex = model.index(row=start-1, parent=index)
        self.update(uindex)
        self.expandAll()

    def generate_airborne_model(self, project: prj.AirborneProject):
        """Generate a Qt Model based on the project structure."""
        raise DeprecationWarning
        model = QStandardItemModel()
        root = model.invisibleRootItem()

        flight_items = {}  # Used to find indexes after creation

        dgs_ico = QIcon(':images/assets/dgs_icon.xpm')
        flt_ico = QIcon(':images/assets/flight_icon.png')

        prj_header = QStandardItem(dgs_ico,
                                   "{name}: {path}".format(name=project.name,
                                                           path=project.projectdir))
        prj_header.setData(project, QtCore.Qt.UserRole)
        prj_header.setEditable(False)
        fli_header = QStandardItem(flt_ico, "Flights")
        fli_header.setEditable(False)
        first_flight = None
        for uid, flight in project.flights.items():
            fli_item = QStandardItem(flt_ico, "Flight: {}".format(flight.name))
            flight_items[flight.uid] = fli_item
            if first_flight is None:
                first_flight = fli_item
            fli_item.setToolTip("UUID: {}".format(uid))
            fli_item.setEditable(False)
            fli_item.setData(flight, QtCore.Qt.UserRole)

            gps_path, gps_uid = flight.gps_file
            if gps_path is not None:
                _, gps_fname = os.path.split(gps_path)
            else:
                gps_fname = '<None>'
            gps = QStandardItem("GPS: {}".format(gps_fname))
            gps.setToolTip("File Path: {}".format(gps_uid))
            gps.setEditable(False)
            gps.setData(gps_uid)  # For future use

            grav_path, grav_uid = flight.gravity_file
            if grav_path is not None:
                _, grav_fname = os.path.split(grav_path)
            else:
                grav_fname = '<None>'
            grav = QStandardItem("Gravity: {}".format(grav_fname))
            grav.setToolTip("File Path: {}".format(grav_path))
            grav.setEditable(False)
            grav.setData(grav_uid)  # For future use

            fli_item.appendRow(gps)
            fli_item.appendRow(grav)

            for line in flight:
                line_item = QStandardItem("Line {}:{}".format(line.start, line.end))
                line_item.setEditable(False)
                fli_item.appendRow(line_item)
            fli_header.appendRow(fli_item)
        prj_header.appendRow(fli_header)

        meter_header = QStandardItem("Meters")
        for meter in project.meters:  # type: prj.AT1Meter
            meter_item = QStandardItem("{}".format(meter.name))
            meter_header.appendRow(meter_item)
        prj_header.appendRow(meter_header)

        root.appendRow(prj_header)
        self.log.debug("Tree Model generated")
        first_index = model.indexFromItem(first_flight)

        # for uid, item in flight_items.items():
        #     self._indexes[uid] = model.indexFromItem(item)
        self._indexes = {uid: model.indexFromItem(item) for uid, item in flight_items.items()}

        return model, first_index

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent, *args, **kwargs):
        context_ind = self.indexAt(event.pos())  # get the index of the item under the click event
        context_focus = self.model().itemFromIndex(context_ind)  # type: ProjectItem
        print(context_focus.uid)

        info_slot = functools.partial(self.flight_info, context_focus)
        plot_slot = functools.partial(self.flight_plot, context_focus)
        menu = QtWidgets.QMenu()
        info_action = QtWidgets.QAction("Info")
        info_action.triggered.connect(info_slot)
        plot_action = QtWidgets.QAction("Plot in new window")
        plot_action.triggered.connect(plot_slot)

        menu.addAction(info_action)
        menu.addAction(plot_action)
        menu.exec_(event.globalPos())
        event.accept()

    def flight_plot(self, item):
        print("Opening new plot for item")
        pass

    def flight_info(self, item):
        data = item.data(QtCore.Qt.UserRole)
        if not (isinstance(data, prj.Flight) or isinstance(data, prj.GravityProject)):
            return
        model = TableModel(['Key', 'Value'])
        model.set_object(data)
        dialog = InfoDialog(model, parent=self)
        dialog.exec_()
        print(dialog.updates)
