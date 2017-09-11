# coding: utf-8

import functools
import logging
import os
from typing import Tuple, List
from threading import Lock

from pandas import Series
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtGui import QColor
from PyQt5.uic import loadUiType

import dgp.lib.project as prj
from dgp.gui.loader import ThreadedLoader
from dgp.lib.plotter import LineGrabPlot
from dgp.lib.types import DataCurve
from dgp.gui.utils import ConsoleHandler, LOG_FORMAT, get_project_file
from dgp.gui.dialogs import ImportData, AddFlight, CreateProject

# Load .ui forms
main_window, _ = loadUiType('gui/ui/main_window.ui')


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
        # self.plotter = LineGrabPlot(2, parent=self)
        # self.plotter.generate_subplots(2)  # TODO: Allow dynamic specification

        # gravity_tab is a widget
        # self.mpl_toolbar = self.plotter.get_toolbar()  # type: QtWidgets.QToolBar
        # self.mpl_toolbar.actions()[4].triggered.connect(self.plotter.toggle_pan)
        # self.mpl_toolbar.actions()[5].triggered.connect(self.plotter.toggle_zoom)
        # self.gravity_plot_layout.addWidget(self.plotter)
        # self.gravity_plot_layout.addWidget(self.mpl_toolbar)

        # Initialize Variables
        # TODO: Change this to use pathlib.Path
        self.import_base_path = os.path.join(os.getcwd(), '../tests')

        # Lock object used as simple Flag supporting the context manager protocol
        self.refocus = Lock()
        self.current_flight = None  # type: prj.Flight
        self.flight_state = {i: {} for i in range(2)}  # TODO: Set this based on number of subplots
        self.flight_data = {}  # Stores DataFrames for loaded flights
        self.flight_plots = {}  # Stores plotter objects for flights
        # self.plot_curves = None  # Initialized in self.init_plot()
        self.active_plot = 0
        self.loader = ThreadedLoader()  # reusable ThreadedLoader for loading large files

        # TESTING
        self.project_tree = ProjectTreeView(parent=self)
        self.update_project()
        self.scan_flights()
        # self.data_tab_layout.addWidget(self.project_tree)
        self.gridLayout_2.addWidget(self.project_tree, 4, 0, 1, 2)
        # TESTING

        # Call sub-initialization functions
        self._init_plots()
        self._init_slots()
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.save_project()
        self.show()

    def _init_plots(self) -> None:
        """
        Initialize plots for flight objects in project.
        This allows us to switch between individual plots without re-plotting giving a vast
        performance increase.
        Returns
        -------
        None
        """
        if self.project is None:
            return
        for flight in self.project:  # type: prj.Flight
            vlayout = QtWidgets.QVBoxLayout()
            f_plot = LineGrabPlot(2)
            # TODO: Call function to plot default data (i.e. gravity + long/cross) here
            self.log.debug("Initialized Flight Plot: {}".format(f_plot))
            toolbar = f_plot.get_toolbar()
            widget = QtWidgets.QWidget()
            vlayout.addWidget(f_plot)
            vlayout.addWidget(toolbar)
            widget.setLayout(vlayout)
            self.flight_plots[flight.uid] = f_plot, widget
            self.gravity_stack.addWidget(widget)

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
        self.resample_value.valueChanged[int].connect(self.resample_rate_changed)

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
            pass

        grav_data = self.flight_data[flight.uid]['gravity']
        gps_data = self.flight_data[flight.uid]['gps']

        # TODO: Move this (and gps plot) into separate functions
        # so we can call this on app startup to pre-plot everything
        if grav_data is not None:
            # Data series for plotting
            gravity = grav_data['gravity']  # type: Series
            long = grav_data['long']
            cross = grav_data['cross']
            curr_plot, stack_widget = self.flight_plots[flight.uid]  # type: LineGrabPlot
            self.gravity_stack.setCurrentWidget(stack_widget)
            # Experimental - so that we only have to draw the plot once, then we switch between
            if not curr_plot.plotted:
                self.log.debug("Plotting gravity channel in subplot 0")
                self.plot_gravity(curr_plot, (gravity, [long, cross]))
            self.log.debug("Already plotted, switching widget stack")

        if gps_data is not None:
            pass

    @staticmethod
    def plot_gravity(plot: LineGrabPlot, data: Tuple):
        # TODO: Change this to accept a dataframe for data, and a tuple of [fields] to plot in respective subplot
        plot.clear()
        for i, series in enumerate(data):
            if not isinstance(series, List):
                plot.plot(plot[i], series.index, series.values, label=series.name)
            else:
                for line in series:
                    plot.plot(plot[i], line.index, line.values, label=line.name)

        plot.draw()
        plot.plotted = True

    def channel_changed(self, item: QtWidgets.QListWidgetItem):
        """
        PyQt Slot:
        Channel selection has changed, update the plot_curves list for the active plot by adding or removing a series
        :param item:
        :return:
        """
        # Refocus Lock is used to signal this function that channel selection events should be ignored
        if self.refocus.locked():
            return

        if item.checkState() == QtCore.Qt.Checked:
            self.log.debug("Channel item selected: {} plotting on plot#: {}".format(item.text(), self.active_plot))
            try:
                self.flight_state[self.active_plot][self.current_flight.uid].add(item.text())
            except KeyError:
                self.flight_state[self.active_plot][self.current_flight.uid] = set()
                self.flight_state[self.active_plot][self.current_flight.uid].add(item.text())
            # self.log.debug("Flight state: {}".format(self.flight_state))
        else:
            # self.log.debug("Channel item deselected: {}".format(item.text()))
            try:
                # self.plot_curves[self.active_plot].remove(data)
                self.flight_state[self.active_plot][self.current_flight.uid].remove(item.text())
            except ValueError:
                pass

        self.draw_plot()

    def resample_rate_changed(self, value) -> None:
        return
        # self.plotter._resample = '{}ms'.format(int(value) * 100)
        # self.draw_plot()

    def get_current_flight_data_channel(self, channel, data='gravity'):
        data_set = self.flight_data[self.current_flight.uid][data]
        if data_set is None:
            return None
        else:
            return data_set.get(channel, None)

    def set_active_plot(self, index) -> None:
        self.log.debug("Setting active plot to: {}".format(index))
        with self.refocus:
            self.active_plot = index

            if self.current_flight is None:
                return
            # Set channel checkboxes to match plot
            checked_channels = [cn for cn in self.flight_state[index].get(self.current_flight.uid, set())]
            for i in range(1, self.gravity_channels.count()):  # Start at 1 to skip channel header
                item = self.gravity_channels.item(i)
                if item.text() in checked_channels:
                    item.setCheckState(QtCore.Qt.Checked)
                else:
                    item.setCheckState(QtCore.Qt.Unchecked)

    #####
    # Project functions
    #####

    def import_data(self) -> None:
        """Load data file (GPS or Gravity) using a background Thread, then hand it off to the project."""
        dialog = ImportData(self.project, self.current_flight)
        if dialog.exec_():
            path, dtype, flt_id = dialog.content
            if self.project is not None:
                flight = self.project.get_flight(flt_id)
                self.log.info("Importing {} file from {} into flight: {}".format(dtype, path, flight.uid))
            else:
                flight = None
            if self.project is not None:
                progress = self.set_progress_bar(25)
                ld = self.loader.load_file(path, dtype, flight, self.project.add_data)
                ld.finished.connect(self.update_project)
                ld.finished.connect(self.save_project)
                ld.finished.connect(self.scan_flights)

                ld.finished.connect(functools.partial(self.set_progress_bar, 100, progress))
                self.current_flight = None  # TODO: Kludge fix to force user to reselect flight after data import

                # cindex = self.prj_tree.currentIndex()
                # self.prj_tree.selectionModel().select(cindex, QtCore.QItemSelectionModel.SelectCurrent)

            else:
                self.log.warning("No active project, not importing.")

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

    def update_project(self) -> None:
        self.log.debug("Update project called")
        if self.project is None:
            return
        # self.prj_tree.setModel(self.project.generate_model())
        # self.prj_tree.expandAll()
        self.project_tree.setModel(self.project.generate_model())
        self.project_tree.expandAll()

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
            return


class ProjectTreeView(QtWidgets.QTreeView):
    def __init__(self, model=None, parent=None):
        super().__init__(parent=parent)
        self.setMinimumSize(QtCore.QSize(0, 300))
        self.setAlternatingRowColors(True)
        self.setAutoExpandDelay(1)
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)
        self.setHeaderHidden(True)
        self.setObjectName('project_tree')
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        # self.setModel(model)
        self.expandAll()

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
        dialog = QtWidgets.QDialog(self)
        dialog.setLayout(QtWidgets.QVBoxLayout())
        dialog.exec_()
        print("Flight info: {}".format(item.text()))



