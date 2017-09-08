# coding: utf-8

import os
import re
import sys
import pickle
import logging
import functools
from threading import Lock
from pathlib import Path

from dgp import resources_rc
from PyQt5 import QtCore, QtWidgets, QtGui, Qt
from PyQt5.QtGui import QColor, QIcon
from PyQt5.uic import loadUiType

import dgp.lib.gravity_ingestor as gi
import dgp.lib.project as prj
from dgp.ui.loader import ThreadedLoader
from dgp.ui.plotter import GeneralPlot
from dgp.lib.types import DataCurve

# Load .ui forms
main_window, _ = loadUiType('ui/main_window.ui')
project_dialog, _ = loadUiType('ui/project_dialog.ui')
data_dialog, _ = loadUiType('ui/data_import_dialog.ui')
splash_screen, _ = loadUiType('ui/splash_screen.ui')

LOG_FORMAT = logging.Formatter(fmt="%(asctime)s - %(module)s:%(funcName)s :: %(message)s", datefmt="%Y%b%d - %H:%M:%S")


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


class ConsoleHandler(logging.Handler):
    """Custom Logging Handler allowing the specification of a custom destination e.g. a QTextEdit area."""
    def __init__(self, destination):
        """
        Initialize the Handler with a destination function to be called on emit().
        Destination should take 2 parameters, however emit will fallback to passing a single parameter on exception.
        :param destination: callable function accepting 2 parameters: (log entry, log level name)
        """
        super().__init__()
        self.dest = destination

    def emit(self, record: logging.LogRecord):
        """Emit the log record, first running it through any specified formatter."""
        entry = self.format(record)
        try:
            self.dest(entry, record.levelname)
        except TypeError:
            self.dest(entry)


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
        self.update_project()

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
        self.plotter = GeneralPlot(parent=self)
        self.plotter.generate_subplots(2)  # TODO: Allow dynamic specification
        self.plotter.set_focus(0)

        self.mpl_toolbar = GeneralPlot.get_toolbar(self.plotter, self.PlotTab)  # type: QtWidgets.QToolBar
        self.plotLayout.addWidget(self.plotter)
        self.plotLayout.addWidget(self.mpl_toolbar)

        # Initialize Variables
        self.import_base_path = os.path.join(os.getcwd(), '../tests')

        # Lock object used as simple Flag supporting the context manager protocol
        self.refocus = Lock()
        self.current_flight = None  # type: prj.Flight
        self.flight_state = {i: {} for i in range(2)}  # TODO: Set this based on number of subplots
        self.flight_data = {}  # Stores DataFrames for loaded flights
        # self.plot_curves = None  # Initialized in self.init_plot()
        self.active_plot = 0
        self.loader = ThreadedLoader()  # reusable ThreadedLoader for loading large files

        # Call sub-initialization functions
        self._init_plot()
        self._init_slots()
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.save_project()
        self.show()

    def _init_plot(self):
        """[Re]Initialize plot object, allowing us to reset/clear the workspace for new data imports"""
        # Initialize dictionary keyed by axes index with empty list to store curve channels
        # self.plot_curves = {x: [] for x in range(len(self.plotter))}
        # self.active_plot = 0
        self.draw_plot()

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
        self.prj_tree.doubleClicked.connect(self.log_tree)
        self.prj_tree.clicked.connect(self.flight_changed)
        # self.prj_tree.currentItemChanged(self.update_channels)

        # Project Control Buttons #
        self.prj_add_flight.clicked.connect(self.add_flight)
        self.prj_import_data.clicked.connect(self.import_data)

        # Channel Panel Buttons #
        # self.selectAllChannels.clicked.connect(self.set_channel_state)
        self.gravity_channels.itemChanged.connect(self.channel_changed)
        self.resample_value.valueChanged[int].connect(self.resample_rate_changed)
        self.resample_value.valueChanged.connect(self.draw_plot)

        # Console Window Actions #
        self.combo_console_verbosity.currentIndexChanged[str].connect(self.set_logging_level)

    def exit(self):
        """PyQt Slot: Exit the PyQt application by closing the main window (self)"""
        self.close()

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
        if text.startswith('Flight:'):
            self.log.debug("Clicked Flight object")
            _, flight_id = text.split(' ')
            flight = self.project.get_flight(flight_id)  # type: prj.Flight
            self.log.debug(flight)
            grav_data = flight.gravity

            if grav_data is not None:
                self.log.debug(grav_data.describe())
            else:
                self.log.debug("No grav data")

        self.log.debug(text)

        self.log.debug(item.toolTip())
        print(dir(item))

    #####
    # Plot functions
    #####

    def draw_plot(self) -> None:
        """
        Draw a linear plot in self.plotter based on the current selected flight and the current
        selected data channels for that flight.
        """
        if self.current_flight is None:
            return
        for ax, flights in self.flight_state.items():
            ax_plots = [DataCurve(cn, self.get_current_flight_data_channel(cn))
                        for cn in flights.get(self.current_flight.uid, set())]

            self.plotter.linear_plot2(ax, *ax_plots)

    def flight_changed(self, index: QtCore.QModelIndex):
        """PyQt Slot: Called upon flight selection change in the project tree view list"""
        item = self.prj_tree.model().itemFromIndex(index)  # type: QtGui.QStandardItem
        flight = item.data(QtCore.Qt.UserRole)  # type: prj.Flight
        self.log.debug("Item Data {} type: {}".format(flight, type(flight)))
        # Checks that this is a Flight object, otherwise we don't care (at this time)
        if not isinstance(flight, prj.Flight):
            return

        # Static Section Headers:
        none_item = QtWidgets.QListWidgetItem('<No Channels Available>')
        none_item.setFlags(QtCore.Qt.NoItemFlags)
        gravity_header = QtWidgets.QListWidgetItem('Gravity Channels:')
        gravity_header.setFlags(QtCore.Qt.NoItemFlags)
        gps_header = QtWidgets.QListWidgetItem('GPS Channels:')
        gps_header.setFlags(QtCore.Qt.NoItemFlags)

        # TODO: this check prevents channels from being updated when a new file is imported - if the flight the file
        # is imported to was already selected
        if self.current_flight == flight:  # So we don't redraw on selection of same flight
            return
        else:
            self.current_flight = flight

        if flight.uid not in self.flight_data.keys():
            # Import data and add to dict
            self.flight_data[flight.uid] = {'gravity': flight.gravity, 'gps': flight.gps}

        if self.flight_data[flight.uid].get('gravity', None) is None:
            self.gravity_channels.clear()
            self.gravity_channels.addItem(none_item)
            self._init_plot()
            return
        grav_channels = self.flight_data[flight.uid]['gravity'].columns

        # Populate the gravity channel list with data columns
        if grav_channels is not None:
            self.gravity_channels.clear()
            self._init_plot()
            self.log.debug(grav_channels)
            self.gravity_channels.addItem(gravity_header)
            for cn in grav_channels:
                cn_widget = QtWidgets.QListWidgetItem(cn)
                self.gravity_channels.addItem(cn_widget)
                # Reapply saved channel state
                if cn in self.flight_state[self.active_plot].get(flight.uid, set()):
                    cn_widget.setCheckState(QtCore.Qt.Checked)
                else:
                    with self.refocus:
                        cn_widget.setCheckState(QtCore.Qt.Unchecked)

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
        self.plotter._resample = '{}ms'.format(int(value) * 100)
        self.draw_plot()


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

                ld.finished.connect(functools.partial(self.set_progress_bar, 100, progress))
                self.current_flight = None  # TODO: Kludge fix to force user to reselect flight after data import
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

    # TODO: This contains deprecated logic, revise and fix
    def open_project(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Open Project Directory", os.path.abspath('..'))
        if not path:
            return

        pattern = re.compile(r'[a-zA-Z0-9]+\.d2p')
        files = [file.name for file in os.scandir(path) if file.is_file()]
        for file in files:
            if re.match(pattern, file):
                self.log.info("Loading project file: {}".format(file))
                self.project = prj.AirborneProject.load(os.path.normpath(os.path.join(path, file)))
                self.update_project()
                return
        self.log.warning("Project file could not be located in directory: {}".format(path))

    def update_project(self) -> None:
        self.log.debug("Update project called")
        if self.project is None:
            return
        self.prj_tree.setModel(self.project.generate_model())
        self.prj_tree.expandAll()

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
        if self.project is None:
            return
        meter = prj.AT1Meter('AT1M-Test')
        flight = prj.Flight(self.project, 'TestFlt', meter)
        self.project.add_flight(flight)
        self.update_project()


class ImportData(QtWidgets.QDialog, data_dialog):
    """

    Rationalization:
    This dialog will be used to import gravity and/or GPS data.
    A drop down box will be populated with the available project flights into which the data will be associated
    User will specify wheter the data is a gravity or gps file (TODO: maybe we can programatically determine the type)
    User will specify file path
        Maybe we can dynamically load the first 5 or so lines of data and display column headings, which would allow user
        to change the headers if necesarry

    This class does not handle the actual loading of data, it only sets up the parameters (path, type etc) for the
    calling class to do the loading.
    """
    def __init__(self, project: prj.AirborneProject=None, flight: prj.Flight=None, *args):
        """

        :param project:
        :param flight: Currently selected flight to auto-select in list box
        :param args:
        """
        super().__init__(*args)
        self.setupUi(self)

        # Setup button actions
        self.button_browse.clicked.connect(self.browse_file)
        self.buttonBox.accepted.connect(self.pre_accept)

        dgsico = Qt.QIcon(':images/assets/geoid_icon.png')

        self.setWindowIcon(dgsico)
        self.path = None
        self.dtype = 'gravity'
        self.flight = flight

        self.flight_map = {}
        if project is not None:
            for flight in project:
                # TODO: Change dict index to human readable value
                self.flight_map[flight.uid] = flight.uid
                self.combo_flights.addItem(flight.uid)
                if flight == self.flight:  # scroll to this item if it matches self.flight
                    self.combo_flights.setCurrentIndex(self.combo_flights.count() - 1)
            for meter in project.meters:
                self.combo_meters.addItem(meter.name)
        else:
            self.combo_flights.setEnabled(False)
            self.combo_meters.setEnabled(False)
            self.combo_flights.addItem("<None>")
            self.combo_meters.addItem("<None>")

        self.file_model = Qt.QFileSystemModel()
        self.init_tree()

    def init_tree(self):
        self.file_model.setRootPath(os.getcwd())
        self.file_model.setNameFilters(["*.csv", "*.dat"])

        self.tree_directory.setModel(self.file_model)
        # self.tree_directory.setRootIndex(file_model.index(os.getcwd()))
        self.tree_directory.scrollTo(self.file_model.index(os.getcwd()))

        self.tree_directory.resizeColumnToContents(0)
        for i in range(1, 4):  # Remove size/date/type columns from view
            self.tree_directory.hideColumn(i)
        self.tree_directory.clicked.connect(self.select_tree_file)

    def select_tree_file(self, index):
        path = Path(self.file_model.filePath(index))
        # TODO: Verify extensions for selected files before setting below
        if path.is_file():
            self.field_path.setText(os.path.normpath(path))
            self.path = path
        else:
            return

    def browse_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Data File", os.getcwd(), "Data (*.dat *.csv)")
        if path:
            self.path = Path(path)
            self.field_path.setText(self.path.name)
            index = self.file_model.index(str(self.path.resolve()))
            self.tree_directory.scrollTo(self.file_model.index(str(self.path.resolve())))
            self.tree_directory.setCurrentIndex(index)

    def pre_accept(self):
        self.dtype = {'GPS Data': 'gps', 'Gravity Data': 'gravity'}.get(self.group_radiotype.checkedButton().text(), 'gravity')
        self.flight = self.flight_map.get(self.combo_flights.currentText(), None)
        self.accept()

    @property
    def content(self) -> (Path, ):
        return self.path, self.dtype, self.flight


class CreateProject(QtWidgets.QDialog, project_dialog):
    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)
        self.prj_create.clicked.connect(self.create_project)
        self.prj_browse.clicked.connect(self.select_dir)

        self._project = None

        # Populate the type selection list
        dgs_airborne = Qt.QListWidgetItem(Qt.QIcon(':images/assets/flight_icon.png'), 'DGS Airborne', self.prj_type_list)
        dgs_airborne.setData(QtCore.Qt.UserRole, 'dgs_airborne')
        self.prj_type_list.setCurrentItem(dgs_airborne)
        dgs_marine = Qt.QListWidgetItem(Qt.QIcon(':images/assets/boat_icon.png'), 'DGS Marine', self.prj_type_list)
        dgs_marine.setData(QtCore.Qt.UserRole, 'dgs_marine')

    def create_project(self):
        """
        Called upon 'Create' button push, do some basic validation of fields then
        accept() if required fields are filled, otherwise color the labels red
        :return: None
        """
        required_fields = {'prj_name': 'label_name', 'prj_dir': 'label_dir'}

        invalid_input = False
        for attr in required_fields.keys():
            if not self.__getattribute__(attr).text():
                self.__getattribute__(required_fields[attr]).setStyleSheet('color: red')
                invalid_input = True
            else:
                self.__getattribute__(required_fields[attr]).setStyleSheet('color: black')

        if not os.path.isdir(self.prj_dir.text()):
            invalid_input = True
            self.label_dir.setStyleSheet('color: red')
            self.label_required.setText("Invalid Directory")
            self.label_required.setStyleSheet('color: red')

        if invalid_input:
            return

        if self.prj_type_list.currentItem().data(QtCore.Qt.UserRole) == 'dgs_airborne':
            name = str(self.prj_name.text()).rstrip()
            path = Path(self.prj_dir.text()).joinpath(name)
            if not path.exists():
                path.mkdir(parents=True)
            self._project = prj.AirborneProject(path, name, self.prj_description.toPlainText().rstrip())
        else:
            self.label_required.setText('Invalid project type (Not Implemented)')
            return

        self.accept()

    def select_dir(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Project Parent Directory")
        if path:
            self.prj_dir.setText(path)

    @property
    def project(self):
        return self._project


class SplashScreen(QtWidgets.QDialog, splash_screen):
    def __init__(self, *args):
        super().__init__(*args)
        self.log = self.setup_logging()
        # Experimental: Add a logger that sets the label_error text
        error_handler = ConsoleHandler(self.write_error)
        error_handler.setFormatter(logging.Formatter('%(message)s'))
        error_handler.setLevel(logging.ERROR)
        self.log.addHandler(error_handler)

        self.setupUi(self)

        self.settings_dir = Path.home().joinpath('AppData\Local\DynamicGravitySystems\DGP')
        self.recent_file = self.settings_dir.joinpath('recent.dict')
        if not self.settings_dir.exists():
            self.log.info("Settings Directory doesn't exist, creating.")
            self.settings_dir.mkdir(parents=True)

        # self.dialog_buttons.accepted.connect(self.accept)
        self.btn_newproject.clicked.connect(self.new_project)
        self.btn_browse.clicked.connect(self.browse_project)
        self.list_projects.currentItemChanged.connect(self.set_selection)

        self.project_path = None  # type: Path
        self.project = None  # type: prj.GravityProject

        self.set_recent_list()
        self.show()

    @staticmethod
    def setup_logging(level=logging.DEBUG):
        root_log = logging.getLogger()
        std_err_handler = logging.StreamHandler(sys.stderr)
        std_err_handler.setLevel(level)
        std_err_handler.setFormatter(LOG_FORMAT)
        root_log.addHandler(std_err_handler)
        return logging.getLogger(__name__)

    def accept(self, project=None):
        """Runs some basic verification before calling QDialog accept()."""
        # Case where project object is passed to accept() (when creating new project)
        if isinstance(project, prj.GravityProject):
            self.log.debug("Opening new project: {}".format(project.name))
            self.add_recent(project)
            super().accept()
            return MainWindow(project)

        # Otherwise check if self.project_path was set to load a project
        if not self.project_path:
            self.log.error("No valid project selected.")
            return
        else:
            try:
                self.project = prj.AirborneProject.load(self.project_path)
            except FileNotFoundError:
                self.log.error("Project could not be loaded from path: {}".format(self.project_path))
                return
            else:
                self.add_recent(self.project)
                super().accept()
                return MainWindow(self.project)

    def set_recent_list(self):
        """Set the 'list_projects' recent file list in the Qt Dialog"""
        if not self.recent_file.is_file():
            self.log.debug("No recent projects")
            none_item = QtWidgets.QListWidgetItem("No Recent Projects", self.list_projects)
            none_item.setFlags(QtCore.Qt.NoItemFlags)
            return
        to_remove = {}
        with self.recent_file.open('rb') as fd:
            recent_dict = pickle.load(fd)  # type: dict
            for name, path in recent_dict.items():
                if not path.exists():
                    self.log.warning("Recent Project: {} path not found {}".format(name, path))
                    to_remove[name] = path
                    continue
                item = QtWidgets.QListWidgetItem('{}  :: {}'.format(name, path))
                item.setToolTip(str(path))
                item.setData(QtCore.Qt.UserRole, path)
                self.list_projects.addItem(item)

    def set_selection(self, item: QtWidgets.QListWidgetItem, *args):
        """Called when a recent item is selected"""
        content = item.text()
        self.project_path = self.get_project(item.data(QtCore.Qt.UserRole))
        if not self.project_path:
            item.setText("{} - Project Moved or Deleted".format(content))

        self.log.debug("Project path set to {}".format(self.project_path))

    def new_project(self):
        """Allow the user to create a new project"""
        dialog = CreateProject()
        if dialog.exec_():
            project = dialog.project
            project.save()
            self.accept(project)
            # self.update()  # Update recent project lists and set it to selected

    def add_recent(self, project):
        """Add a project to the recent projects tracking dictionary and pickle it."""
        if self.recent_file.exists():
            with self.recent_file.open('rb') as rd:
                recent = pickle.load(rd)
        else:
            recent = {}
        recent[project.name] = Path(project.projectdir)

        with self.recent_file.open('wb') as wd:
            pickle.dump(recent, wd)
        self.log.debug('Added project: {} to recent projects file'.format(project.name))

    # TODO: Not working, need to open pickle separately to read/write?
    def remove_recents(self, remove: dict):
        """
        Remove recent projects from recent listing - checking name and path as it is possible a project may be called
        the same as another in a different path.
        :param remove: dict: {name: path} of recent projects to remove from listing
        :return:
        """
        self.log.debug("Removing recent items")
        with self.recent_file.open('r+b') as fd:
            recent = pickle.load(fd)
            print(recent)
            # new_recent = {k: v for k, v in recent.items() if k not in remove.keys()}
            new_recent = {k: v for k, v in recent.items() if not remove.get(k, None) == v}
            print(new_recent)

            pickle.dump(new_recent, fd)

    def browse_project(self):
        """Allow the user to browse for a project directory and load."""
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if not path:
            return

        prj_file = self.get_project(path)
        if not prj_file:
            self.label_error.setText("Invalid project directory.")
            self.log.warning("No valid project files found in directory: {}.".format(path))
            return

        self.project_path = prj_file
        self.accept()  # pre_accept takes the self.project_path file and loads the project.

    def write_error(self, msg, level=None):
        self.label_error.setText(msg)

    @staticmethod
    def get_project(path: str):
        """
        Attempt to retrieve a project file (*.d2p) from the given dir path, otherwise signal failure by returning False
        :param path: str or pathlib.Path : Directory path to project
        :return: pathlib.Path : absolute path to *.d2p file if found, else False
        """
        _path = Path(path)
        for child in sorted(_path.glob('*.d2p')):
            return child.resolve()
        return False

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    form = SplashScreen()
    sys.exit(app.exec_())
