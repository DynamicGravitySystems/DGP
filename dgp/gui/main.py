# coding: utf-8

import functools
import logging
import os
from typing import Tuple, List, Dict

from pandas import Series, DataFrame
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtBoundSignal
from PyQt5.QtGui import QColor
from PyQt5.uic import loadUiType

import dgp.lib.project as prj
import dgp.lib.trajectory_ingestor as ti
from dgp.gui.loader import LoadFile
from dgp.lib.plotter import LineGrabPlot
from dgp.gui.utils import ConsoleHandler, LOG_FORMAT, get_project_file
from dgp.gui.dialogs import ImportData, AddFlight, CreateProject

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
        # self.update_project()

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

        # Initialize Variables
        # TODO: Change this to use pathlib.Path
        self.import_base_path = os.path.join(os.getcwd(), '../tests')

        # Lock object used as simple Flag supporting the context manager protocol
        self.current_flight = None  # type: prj.Flight
        self.flight_data = {}  # Stores DataFrames for loaded flights
        self.flight_plots = {}  # Stores plotter objects for flights
        # self.plot_curves = None  # Initialized in self.init_plot()

        # TESTING
        self.project_tree = ProjectTreeView(parent=self)
        self.scan_flights()
        # self.data_tab_layout.addWidget(self.project_tree)
        self.gridLayout_2.addWidget(self.project_tree, 1, 0, 1, 2)
        # TESTING

    def load(self):
        self._init_plots()
        self._init_slots()
        self.update_project(signal_flight=True)
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.save_project()
        self.show()
        try:
            self.progress.disconnect()
            self.status.disconnect()
        except TypeError:
            # This will happen if there are no slots connected
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
        for i, flight in enumerate(self.project):  # type: prj.Flight
            if flight.uid in self.flight_plots:
                continue
            vlayout = QtWidgets.QVBoxLayout()
            f_plot = LineGrabPlot(2, title=flight.name)
            toolbar = f_plot.get_toolbar()
            widget = QtWidgets.QWidget()
            vlayout.addWidget(f_plot)
            vlayout.addWidget(toolbar)
            widget.setLayout(vlayout)
            self.flight_plots[flight.uid] = f_plot, widget
            self.gravity_stack.addWidget(widget)
            gravity = self.flight_data[flight.uid].get('gravity')
            if gravity is not None:
                self.plot_gravity(f_plot, gravity, {0: 'gravity', 1: ['long', 'cross']})
            self.log.debug("Initialized Flight Plot: {}".format(f_plot))
            self.status.emit('Flight Plot {} Initialized'.format(flight.name))
            self.progress.emit(i+1)

    def _init_slots(self):
        """Initialize PyQt Signals/Slots for UI Buttons and Menus"""

        # File Menu Actions #
        self.action_exit.triggered.connect(self.exit)
        self.action_file_new.triggered.connect(self.new_project)
        self.action_file_open.triggered.connect(self.open_project)
        self.action_file_save.triggered.connect(self.save_project)

        # Project Menu Actions #
        self.action_import_data.triggered.connect(self.import_data)
        self.action_add_flight.triggered.connect(self.add_flight)

        # Project Tree View Actions #
        # self.prj_tree.doubleClicked.connect(self.log_tree)
        # self.prj_tree.clicked.connect(self.flight_changed)
        # self.prj_tree.currentItemChanged(self.update_channels)
        self.project_tree.clicked.connect(self.flight_changed)

        # Project Control Buttons #
        self.prj_add_flight.clicked.connect(self.add_flight)
        self.prj_import_data.clicked.connect(self.import_data)

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
        log_color = {'DEBUG': QColor('Blue'), 'INFO': QColor('Green'), 'WARNING': QColor('Red'),
                     'ERROR': QColor('Pink'), 'CRITICAL': QColor('Orange')}.get(level, QColor('Black'))

        self.text_console.setTextColor(log_color)
        self.text_console.append(str(text))
        self.text_console.verticalScrollBar().setValue(self.text_console.verticalScrollBar().maximum())

    # TODO: Delete after testing
    def log_tree(self, index: QtCore.QModelIndex):
        item = self.prj_tree.model().itemFromIndex(index)  # type: QtWidgets.QListWidgetItem
        text = str(item.text())
        return
        # if text.startswith('Flight:'):
        #     self.log.debug("Clicked Flight object")
        #     _, flight_id = text.split(' ')
        #     flight = self.project.get_flight(flight_id)  # type: prj.Flight
        #     self.log.debug(flight)
        #     grav_data = flight.gravity
        #
        #     if grav_data is not None:
        #         self.log.debug(grav_data.describe())
        #     else:
        #         self.log.debug("No grav data")
        #
        # self.log.debug(text)
        #
        # self.log.debug(item.toolTip())
        # print(dir(item))

    #####
    # Plot functions
    #####

    def scan_flights(self):
        """Scan flights and load data into self.flight_data"""
        self.log.info("Rescanning and loading flight data.")
        for flight in self.project:
            if flight.uid not in self.flight_data:
                self.flight_data[flight.uid] = {'gravity': flight.gravity, 'gps': flight.gps}
            else:
                self.flight_data[flight.uid].update({'gravity': flight.gravity, 'gps': flight.gps})

    def flight_changed(self, index: QtCore.QModelIndex) -> None:
        """
        PyQt Slot called upon change in flight selection using the Project Tree View.
        When a new flight is selected we want to plot the gravity channel in subplot 0, with cross and long in subplot 1
        GPS data will be plotted in the GPS tab on its own plot.
        Parameters
        ----------
        index : QtCore.QModelIndex
            Model index referencing the newly selected TreeView Item

        Returns
        -------
        None

        """
        qitem = self.project_tree.model().itemFromIndex(index)  # type: QtGui.QStandardItem
        if qitem is None:
            return
        qitem_data = qitem.data(QtCore.Qt.UserRole)

        if not isinstance(qitem_data, prj.Flight):
            # Return as we're not interested in handling non-flight selections at this time
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
            self.log.debug("Already have a plot for this flight: {}".format(flight.name))
            curr_plot, stack_widget = self.flight_plots[flight.uid]  # type: LineGrabPlot
            self.gravity_stack.setCurrentWidget(stack_widget)
            pass

        grav_data = self.flight_data[flight.uid].get('gravity', None)
        gps_data = self.flight_data[flight.uid].get('gps', None)

        # TODO: Move this (and gps plot) into separate functions
        # so we can call this on app startup to pre-plot everything
        if grav_data is not None:
            if not curr_plot.plotted:
                self.log.debug("Plotting gravity channel in subplot 0")
                self.plot_gravity(curr_plot, grav_data, {0: 'gravity', 1: ['long', 'cross']})
            self.log.debug("Already plotted, switching widget stack")

        if gps_data is not None:
            self.log.debug("Flight has GPS Data")

    @staticmethod
    def plot_gravity(plot: LineGrabPlot, data: DataFrame, fields: Dict):
        plot.clear()
        for index in fields:
            if isinstance(fields[index], str):
                series = data.get(fields[index])  # type: Series
                plot.plot(plot[index], series.index, series.values, label=series.name)
                continue
            for field in fields[index]:
                series = data.get(field)  # type: Series
                plot.plot(plot[index], series.index, series.values, label=series.name)
        plot.draw()
        plot.plotted = True

    def plot_gps(self):
        pass

    #####
    # Project functions
    #####

    def import_data(self) -> None:
        """Load data file (GPS or Gravity) using a background Thread, then hand it off to the project."""
        dialog = ImportData(self.project, self.current_flight)
        if dialog.exec_():
            path, dtype, flt_id = dialog.content
            flight = self.project.get_flight(flt_id)
            self.log.critical("Data Type is: {}".format(dtype))
            self.log.info("Importing {} file from {} into flight: {}".format(dtype, path, flight.uid))

            self.log.debug("Importing file using new thread method")
            ld2 = LoadFile(path, dtype, flight, self)
            ld2.data.connect(self.project.add_data)
            ld2.loaded.connect(functools.partial(self.update_project, signal_flight=True))
            ld2.loaded.connect(self.save_project)
            ld2.loaded.connect(self.scan_flights)
            self.current_flight = None
            ld2.start()

            # gps_fields = ['mdy', 'hms', 'lat', 'lon', 'ell_ht', 'ortho_ht', 'num_sats', 'pdop']
            # self.gps_data = ti.import_trajectory(path, columns=gps_fields, skiprows=1)

    def new_project(self) -> QtWidgets.QMainWindow:
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

    # TODO: This will eventually require a dialog to allow selection of project type
    def open_project(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Open Project Directory", os.path.abspath('..'))
        if not path:
            return

        prj_file = get_project_file(path)  # TODO: Migrate this func to a utility module
        if prj_file is None:
            self.log.warning("No project file's found in directory: {}".format(path))
            return
        self.project.save()
        self.project = prj.AirborneProject.load(prj_file)
        self.update_project()
        return

    def update_project(self, signal_flight=False) -> None:
        self.log.debug("Update project called")
        if self.project is None:
            return
        # self.prj_tree.setModel(self.project.generate_model())
        # self.prj_tree.expandAll()
        model, index = self.project.generate_model()
        # self.project_tree.refresh(index)
        self.project_tree.setModel(model)
        self.project_tree.expandAll()
        self.project_tree.setCurrentIndex(index)
        if signal_flight:
            self.flight_changed(index)

    def save_project(self) -> None:
        if self.project is None:
            return
        if self.project.save():
            self.setWindowTitle(self.title + ' - {} [*]'.format(self.project.name))
            self.setWindowModified(False)
            self.log.info("Project saved.")
        else:
            self.log.info("Error saving project.")

    @autosave
    def add_flight(self) -> None:
        # TODO: do I need these checks? self.project should not ever be None
        if self.project is None:
            return
        dialog = AddFlight(self.project)
        if dialog.exec_():
            self.log.info("Adding flight:")
            flight = dialog.flight
            self.project.add_flight(flight)
            self.update_project()
            self.scan_flights()
            self._init_plots()
            return


class ProjectTreeView(QtWidgets.QTreeView):
    def __init__(self, model=None, project=None, parent=None):
        super().__init__(parent=parent)
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

    def refresh(self, curr_index=None):
        """Regenerate model and set current selection to curr_index"""
        # self.generate_airborne_model()
        if curr_index is not None:
            self.setCurrentIndex(curr_index)
        self.expandAll()

    def generate_airborne_model(self):
        pass

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent, *args, **kwargs):
        context_ind = self.indexAt(event.pos())
        context_focus = self.model().itemFromIndex(context_ind)
        print(context_focus)
        print(context_focus.text())

        info_slot = functools.partial(self.flight_info, context_focus)
        menu = QtWidgets.QMenu()
        info_action = QtWidgets.QAction("Info")
        info_action.triggered.connect(info_slot)
        menu.addAction(info_action)
        menu.exec_(event.globalPos())
        event.accept()

    def flight_info(self, item):
        data = item.getData(QtCore.Qt.UserRole)
        if isinstance(data, prj.Flight):
            dialog = QtWidgets.QDialog(self)
            dialog.setLayout(QtWidgets.QVBoxLayout())
            dialog.exec_()
            print("Flight info: {}".format(item.text()))
        else:
            print("Info event: Not a flight")



