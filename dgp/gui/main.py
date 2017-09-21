# coding: utf-8

import os
import pathlib
import functools
import logging
from typing import Tuple, List, Dict

from pandas import Series, DataFrame
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtBoundSignal
from PyQt5.QtGui import QColor, QStandardItemModel, QStandardItem, QIcon
from PyQt5.uic import loadUiType

import dgp.lib.project as prj
from dgp.gui.loader import LoadFile
from dgp.lib.plotter import LineGrabPlot
from dgp.gui.utils import ConsoleHandler, LOG_FORMAT, get_project_file
from dgp.gui.dialogs import ImportData, AddFlight, CreateProject, InfoDialog
from dgp.gui.models import TableModel

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

    def __init__(self, project: prj.GravityProject=None, *args):
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
        # TODO: Change this to use pathlib.Path
        self.import_base_path = os.path.join(os.getcwd(), '../tests')

        self.current_flight = None  # type: prj.Flight
        self.current_flight_index = QtCore.QModelIndex()  # type: QtCore.QModelIndex
        self.tree_index = None  # type: QtCore.QModelIndex
        self.flight_plots = {}  # Stores plotter objects for flights

        self.project_tree = ProjectTreeView(parent=self, project=self.project)
        self.project_tree.setMinimumWidth(290)
        self.project_dock_grid.addWidget(self.project_tree, 0, 0, 1, 2)

    def load(self):
        self._init_plots()
        self._init_slots()
        # self.update_project(signal_flight=True)
        self.project_tree.refresh()
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.save_project()
        self.show()
        try:
            self.progress.disconnect()
            self.status.disconnect()
        except TypeError:  # This will happen if there are no slots connected
            pass

    def _init_plots(self) -> None:
        """
        Initialize plots for flight objects in project.
        This allows us to switch between individual plots without re-plotting giving a vast
        performance increase.
        Returns
        -------
        None
        """
        self.progress.emit(0)
        if self.project is None:
            return
        for i, flight in enumerate(self.project):  # type: int, prj.Flight
            if flight.uid in self.flight_plots:
                continue

            plot, widget = self._new_plot_widget(flight.name, rows=3)

            self.flight_plots[flight.uid] = plot, widget
            self.gravity_stack.addWidget(widget)
            gravity = flight.gravity
            if gravity is not None:
                self.plot_time_series(plot, gravity, {0: 'gravity', 1: ['long', 'cross']})

            if flight.eotvos is not None:
                print(flight.eotvos.columns)
                self.plot_time_series(plot, flight.eotvos, {2: 'eotvos'})

            self.log.debug("Initialized Flight Plot: {}".format(plot))
            self.status.emit('Flight Plot {} Initialized'.format(flight.name))
            self.progress.emit(i+1)

    @staticmethod
    def _new_plot_widget(title, rows=2):
        plot = LineGrabPlot(rows, title=title)
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

    # Experimental
    def set_progress_bar(self, value=100, progress=None):
        if progress is None:
            progress = QtWidgets.QProgressBar()
            progress.setValue(value)
            self.statusBar().addWidget(progress)
        else:
            progress.setValue(value)

        return progress

    def set_logging_level(self, name: str):
        """PyQt Slot: Changes logging level to passed string logging level name."""
        self.log.debug("Changing logging level to: {}".format(name))
        # TODO: Replace this with gui.utils LOG_COLOR_MAP
        level = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARNING, 'error': logging.ERROR,
                 'critical': logging.CRITICAL}[name.lower()]
        self.log.setLevel(level)

    def write_console(self, text, level):
        """PyQt Slot: Log a message to the GUI console"""
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
        qitem = self.project_tree.model().itemFromIndex(index)  # type: QtGui.QStandardItem
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

        # TODO: Move this (and gps plot) into separate functions
        # so we can call this on app startup to pre-plot everything
        if flight.gravity is not None:
            if not grav_plot.plotted:
                self.plot_time_series(grav_plot, flight.gravity, {0: 'gravity', 1: ['long', 'cross']})

        if flight.gps is not None:
            self.log.debug("Flight has GPS Data")

    def redraw(self, flt_id: str):
        plot, _ = self.flight_plots[flt_id]
        flt = self.project.get_flight(flt_id)  # type: prj.Flight
        if flt.gravity is not None:
            self.plot_time_series(plot, flt.gravity, {0: 'gravity', 1: ['long', 'cross']})
        if flt.gps is not None:
            self.plot_time_series(plot, flt.eotvos, {2: 'eotvos'})

    @staticmethod
    def plot_time_series(plot: LineGrabPlot, data: DataFrame, fields: Dict):
        plot.clear()
        for index in fields:
            if isinstance(fields[index], str):
                series = data.get(fields[index])  # type: Series
                plot.plot2(plot[index], series)
                continue
            for field in fields[index]:
                series = data.get(field)  # type: Series
                plot.plot2(plot[index], series)
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

    def import_data(self, path: pathlib.Path, dtype: str, flight: prj.Flight):
        self.log.info("Importing <{dtype}> from: Path({path}) into <Flight({name})>".format(dtype=dtype, path=str(path),
                                                                                            name=flight.name))
        if path is None:
            return False
        loader = LoadFile(path, dtype, flight.uid, self)

        # Curry functions to execute on thread completion.
        add_data = functools.partial(self.project.add_data, flight_uid=flight.uid)
        tree_refresh = functools.partial(self.project_tree.refresh, curr_flightid=flight.uid)
        redraw_flt = functools.partial(self.redraw, flight.uid)
        prog = self.progress_dialog("Loading", 0, 0)

        loader.data.connect(add_data)
        loader.progress.connect(prog.setValue)
        loader.loaded.connect(tree_refresh)
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
        dialog = ImportData(self.project, self.current_flight)
        if dialog.exec_():
            path, dtype, flt_id = dialog.content
            flight = self.project.get_flight(flt_id)
            plot, _ = self.flight_plots[flt_id]
            plot.plotted = False
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

        prj_file = get_project_file(path)  # TODO: Migrate this func to a utility module
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

            plot, widget = self._new_plot_widget(flight.name, rows=3)
            self.gravity_stack.addWidget(widget)
            self.flight_plots[flight.uid] = plot, widget
            self.project_tree.refresh(curr_flightid=flight.uid)
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
        self.setHeaderHidden(True)
        self.setObjectName('project_tree')
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.refresh()
        # self.setModel(model)
        # self.expandAll()

    def refresh(self, curr_index=None, curr_flightid=None):
        """Regenerate model and set current selection to curr_index"""
        model, index = self.generate_airborne_model(self._project)
        self.setModel(model)
        if curr_index is not None:
            index = curr_index
        elif curr_flightid is not None:
            index = self._indexes[curr_flightid]

        self.setCurrentIndex(index)
        self.clicked.emit(index)
        self.expandAll()

    def generate_airborne_model(self, project: prj.AirborneProject):
        """Generate a Qt Model based on the project structure."""
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
        context_ind = self.indexAt(event.pos())
        context_focus = self.model().itemFromIndex(context_ind)

        info_slot = functools.partial(self.flight_info, context_focus)
        menu = QtWidgets.QMenu()
        info_action = QtWidgets.QAction("Info")
        info_action.triggered.connect(info_slot)
        menu.addAction(info_action)
        menu.exec_(event.globalPos())
        event.accept()

    def flight_info(self, item):
        data = item.data(QtCore.Qt.UserRole)
        if not (isinstance(data, prj.Flight) or isinstance(data, prj.GravityProject)):
            return
        model = TableModel(['Key', 'Value'])
        model.set_object(data)
        dialog = InfoDialog(model, parent=self)
        dialog.exec_()
        print(dialog.updates)
