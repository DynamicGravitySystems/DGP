# coding: utf-8

import os
import re
import sys
import pickle
import logging
from pathlib import Path

from dgp import resources_rc
from PyQt5 import QtCore, QtWidgets, QtGui, Qt
from PyQt5.QtGui import QColor, QIcon
from PyQt5.uic import loadUiType

import dgp.lib.gravity_ingestor as gi
import dgp.lib.project as prj
from dgp.ui.loader import ThreadedLoader
from dgp.ui.plotter import GeneralPlot

# Load .ui forms
main_window, _ = loadUiType('ui/main_window.ui')
project_dialog, _ = loadUiType('ui/project_dialog.ui')
data_dialog, _ = loadUiType('ui/data_import_dialog.ui')
splash_screen, _ = loadUiType('ui/splash_screen.ui')


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
    def __init__(self, project=None, *args):
        super().__init__(*args)

        self.setupUi(self)  # Set up ui within this class - which is base_class defined by .ui file
        self.statusBar().showMessage('Initializing Application', 1000)
        self.title = 'Dynamic Gravity Processor'

        # Setup logging
        self.root_log = logging.getLogger()
        self.root_log.setLevel(logging.DEBUG)
        handler = ConsoleHandler(self.write_console)
        self.log_fmtr = logging.Formatter(fmt="%(asctime)s - %(module)s:%(funcName)s :: %(message)s",
                                          datefmt="%Y%b%d - %H:%M:%S")
        handler.setFormatter(self.log_fmtr)
        stdhandler = logging.StreamHandler(sys.stdout)
        stdhandler.setFormatter(self.log_fmtr)
        self.root_log.addHandler(handler)
        self.root_log.addHandler(stdhandler)
        self.log = logging.getLogger(__name__)

        # See http://doc.qt.io/qt-5/stylesheet-examples.html#customizing-qtreeview
        # TODO: Make arrow right/down icons for expanding the tree
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
        self.plotter.generate_subplots(2)
        self.plotter.set_focus(0)

        self.mpl_toolbar = GeneralPlot.get_toolbar(self.plotter, parent=self)
        self.plotLayout.addWidget(self.plotter)
        self.plotLayout.addWidget(self.mpl_toolbar)

        # Initialize Variables
        self.import_base_path = os.path.join(os.getcwd(), '../tests')
        self.refocus_flag = False  # Flag used when changing between plots, to avoid recalc_plots call
        self.plot_curves = None
        self.active_plot = 0
        # self.active_project = None
        self.loader = ThreadedLoader()  # reusable ThreadedLoader for loading large files

        # Call sub-initialization functions
        self.init_plot()
        self.init_slots()
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.statusBar().clearMessage()
        self.project = None  # type: prj.AirborneProject
        self.show_splash()
        self.setWindowTitle(self.title + ' - {} [*]'.format(self.project.name))
        # self.setWindowModified(True)
        self.show()

    def show_splash(self):
        """Show the Program splash screen prompting user to load or create a project."""
        splash = SplashScreen()
        if splash.exec_():
            self.project = splash.project
            self.update_project()
            self.log.info("Loaded project: {}".format(self.project.name))
            print("selected a project")
        else:
            self.log.debug("Exiting program")
            sys.exit(0)

    def init_plot(self):
        """Initialize plot object, allowing us to reset/clear the workspace for new data imports"""
        # Initialize dictionary keyed by axes index with empty list to store curve channels
        self.plot_curves = {x: [] for x in range(len(self.plotter))}
        self.active_plot = 0
        # self.draw_plot()

    def init_slots(self):
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
        self.prj_tree.clicked.connect(self.update_channels)

        # Project Control Buttons #
        self.prj_add_flight.clicked.connect(self.add_flight)
        self.prj_import_data.clicked.connect(self.import_data)

        # Channel Panel Buttons #
        self.selectAllChannels.clicked.connect(self.set_channel_state)
        self.list_channels.itemChanged.connect(self.recalc_plots)
        self.resample_value.valueChanged.connect(self.draw_plot)

        # Console Window Actions #
        self.combo_console_verbosity.currentIndexChanged[str].connect(self.set_logging_level)


    def exit(self):
        """Exit the PyQt application by closing the main window (self)"""
        self.close()

    def set_logging_level(self, name: str):
        self.log.debug("Changing logging level to: {}".format(name))
        level = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARNING, 'error': logging.ERROR,
                     'critical': logging.CRITICAL}[name.lower()]

        self.root_log.setLevel(level)

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

    def update_channels(self, index: QtCore.QModelIndex):
        self.log.debug("Index: {} selected".format(index))
        pass

    def write_console(self, text, level):
        """Log a message to the GUI console"""
        log_color = {'DEBUG': QColor('Blue'), 'INFO': QColor('Green'), 'WARNING': QColor('Red'),
                     'ERROR': QColor('Pink'), 'CRITICAL': QColor('Orange')}.get(level, QColor('Black'))

        self.text_console.setTextColor(log_color)
        self.text_console.append(str(text))
        self.text_console.verticalScrollBar().setValue(self.text_console.verticalScrollBar().maximum())

    def resample_rate(self):
        ms = self.resample_value.value() * 100
        return "{}ms".format(ms)

    # TODO: This needs to be reworked with the project architecture
    def draw_plot(self, *args):
        # TODO: Figure out a way to allow redrawing of all plots at once
        if self.grav_data is not None:
            checked = self.get_selected_channels()
            series = [self.grav_data[x] for x in checked]
            self.plotter._resample = self.resample_rate()
            self.plotter.linear_plot2(self.active_plot, *series)
        else:
            return

    def set_active_plot(self, index):
        self.refocus_flag = True
        self.active_plot = index
        self.set_channel_state(state=0)  # Set all channels to cleared
        if len(self.plot_curves[index]):
            self.set_channel_state(*self.plot_curves[index], state=2)
        self.refocus_flag = False

    def recalc_plots(self, *list_items):
        if self.refocus_flag:
            return
        for item in list_items:
            if item.checkState() == 2:
                self.plot_curves[self.active_plot].append(item.text())
            else:
                self.plot_curves[self.active_plot].remove(item.text())
        self.draw_plot()

    def get_selected_channels(self):
        checked = []
        for i in range(self.list_channels.count()):
            cn = self.list_channels.item(i)
            if cn.checkState() == 2:
                checked.append(cn.text())
        return checked

    def set_channel_state(self, *channel, state=2):
        """
        Set the checked state of the specified channel(s)
        If no channels are passed as arguments the function will act on all available channels
        :param channel: [(str)] channel name
        :param state: (int) QListWidgetItem CheckState value 0: unchecked 1: partially checked 2: checked
        """
        self.log.debug("Setting state to {}, channel is {}".format(state, channel))
        if not channel:
            for i in range(self.list_channels.count()):
                self.list_channels.item(i).setCheckState(state)
            return

        for i in range(self.list_channels.count()):
            if self.list_channels.item(i).text() in channel:
                # TODO: check state parameter for validity
                self.list_channels.item(i).setCheckState(state)
            else:
                continue

    # TODO: Delete this in favor of import_data
    def import_gravity(self):
        # getOpenFileName returns a tuple of (path, filter), we only need the path
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Gravity Data File",
                                                        self.import_base_path,
                                                        "Data Files (*.csv *.dat)")
        if path:
            try:
                # TODO: Thread this to allow for responsive UI during large imports
                self.grav_data = gi.read_at1m(path)
            except OSError:
                self.log.error('Error importing Gravity data file')
            else:
                # Set up the channel list for each column in gravity data
                self.set_channel_state(state=0)
                self.init_plot()  # Reinitialize plot to clear old data
                self.log.info('Data file loaded')
                self.prj_info.append("File path:\n{}".format(path))
                self.list_channels.clear()
                for col in self.grav_data.columns:
                    item = QtWidgets.QListWidgetItem(str(col))
                    item.setCheckState(QtCore.Qt.Unchecked)
                    self.list_channels.addItem(item)
                self.set_channel_state('gravity')

                self.log.info(str(self.grav_data.describe()))

    def import_data(self):
        dialog = ImportData(self.project)
        if dialog.exec_():
            path, dtype, flt_id = dialog.content
            if self.project is not None:
                flight = self.project.get_flight(flt_id)
                self.log.info("Importing {} file from {} into flight: {}".format(dtype, path, flight.uid))
            else:
                flight = None
            if self.project is not None:
                self.loader.load_file(path, dtype, flight, self.project.add_data)
                self.loader.add_hook(self.update_project)

            else:
                self.log.warning("No active project, not importing.")

            # gps_fields = ['mdy', 'hms', 'lat', 'lon', 'ell_ht', 'ortho_ht', 'num_sats', 'pdop']
            # self.gps_data = ti.import_trajectory(path, columns=gps_fields, skiprows=1)

    def new_project(self):
        dialog = CreateProject()
        if dialog.exec_():
            self.log.info("Creating new project")
            self.project = dialog.project
            self.project.save()
            self.log.debug(str(self.project))
            self.update_project()
        else:
            return

    def open_project(self):
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

    def update_project(self):
        self.log.debug("Update project called")
        if self.project is None:
            return
        self.prj_tree.setModel(self.project.generate_model())
        self.prj_tree.expandAll()

    def save_project(self):
        if self.project is None:
            return
        if self.project.save():
            self.setWindowModified(False)
            self.log.info("Project saved.")
        else:
            self.log.info("Error saving project.")

    # TODO: Add decorator that will call update_project for functions that affect project structure
    @autosave
    def add_flight(self):
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
    def __init__(self, project: prj.AirborneProject=None, *args):
        super().__init__(*args)
        self.setupUi(self)

        # Setup button actions
        self.button_browse.clicked.connect(self.select_file)
        self.buttonBox.accepted.connect(self.pre_accept)

        # TODO: Remove this reference - use global imported icon resources
        dgsico = Qt.QIcon(':images/assets/geoid_icon.png')

        self.setWindowIcon(dgsico)
        self.path = None
        self.dtype = 'gravity'
        self.flight = None

        self.flight_map = {}
        if project is not None:
            for flight in project:
                # TODO: Change dict index to human readable value
                self.flight_map[flight.uid] = flight.uid
                self.combo_flights.addItem(flight.uid)
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
        path = self.file_model.filePath(index)
        # TODO: Verify extensions for selected files before setting below
        if os.path.isfile(path):
            self.field_path.setText(os.path.normpath(path))
            self.path = path
        else:
            return

    def select_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Data File", os.getcwd(), "Data (*.dat *.csv)")
        if path:
            self.path = path
            self.field_path.setText(os.path.normpath(path))

    def pre_accept(self):
        self.dtype = {'GPS Data': 'gps', 'Gravity Data': 'gravity'}.get(self.group_radiotype.checkedButton().text(), 'gravity')
        self.flight = self.flight_map.get(self.combo_flights.currentText(), None)
        self.accept()

    @property
    def content(self):
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
        self.log = logging.getLogger(__name__)
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

        self.project_path = None
        self.project = None

        # TODO: Move this all to a function that updates list_projects
        # TODO: Create function that loads all recent project pickles to retrieve info e.g. Name, Type for display
        self.set_recent_list()

        self.show()

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
                item = QtWidgets.QListWidgetItem(name)
                item.setToolTip(str(path))
                item.setData(QtCore.Qt.UserRole, path)
                self.list_projects.addItem(item)
        # self.remove_recents(to_remove)

    def accept(self):
        """Runs some basic verification before calling QDialog accept()."""
        if not self.project_path:
            self.label_error.setText("No valid project selected.")
            return
        else:
            self.project = prj.AirborneProject.load(self.project_path)
            self.add_recent(self.project)
            super().accept()
            print("Accepted")

    def set_selection(self, item: QtWidgets.QListWidgetItem, *args):
        """Called when a recent item is selected"""
        content = item.text()
        self.project_path = self.get_project(item.data(QtCore.Qt.UserRole))
        if not self.project_path:
            item.setText("{} - Project Moved or Deleted".format(content))

        self.log.debug("Project path set to {}".format(self.project_path))

    def new_project(self):
        """Allow the user to create a new project"""
        prj_dialog = CreateProject()
        if prj_dialog.exec_():
            self.project = prj_dialog.project
            self.project.save()
            self.add_recent(self.project)
            self.accept()
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

    def remove_recents(self, remove: dict):
        """
        Remove recent projects from recent listing - checking name and path as it is possible a project may be called
        the same as another in a different path.
        :param remove: dict: {name: path} of recent projects to remove from listing
        :return:
        """
        print("Removing recent items")
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
    form = MainWindow()
    sys.exit(app.exec_())
