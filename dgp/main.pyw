# coding: utf-8

import os
import re
import sys

from dgp import resources_rc
from PyQt5 import QtCore, QtWidgets, QtGui, Qt
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


class MainWindow(QtWidgets.QMainWindow, main_window):
    def __init__(self, *args):
        super().__init__(*args)

        self.setupUi(self)  # Set up ui within this class - which is base_class defined by .ui file
        self.statusBar().showMessage('Initializing Application', 1000)
        self.title = 'Dynamic Gravity Processor'


        # See http://doc.qt.io/qt-5/stylesheet-examples.html#customizing-qtreeview
        self.setStyleSheet("""
            QTreeView::item {
                
            }
            QTreeView::branch:has-siblings:adjoins-them {
                border: 1px solid black;
            }
            QTreeView::branch {
                background: palette(base);
            }

            QTreeView::branch:has-siblings:!adjoins-item {
                background: cyan;
            }

            QTreeView::branch:has-siblings:adjoins-item {
                background: orange;
            }

            QTreeView::branch:!has-children:!has-siblings:adjoins-item {
                background: blue;
            }

            QTreeView::branch:closed:has-children:has-siblings {
                background: pink;
            }

            QTreeView::branch:has-children:!has-siblings:closed {
                background: gray;
            }

            QTreeView::branch:open:has-children:has-siblings {
                background: magenta;
            }

            QTreeView::branch:open:has-children:!has-siblings {
                background: green;
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
        self.grav_file = None
        self.grav_data = None
        self.gps_data = None
        self.refocus_flag = False
        self.plot_curves = None
        self.active_plot = 0
        # self.active_project = None
        self.loader = ThreadedLoader()  # ThreadedLoader for loading large files

        # Call sub-initialization functions
        self.init_plot()
        self.init_slots()
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.statusBar().clearMessage()
        self.active_project = None  # type: prj.AirborneProject
        self.show_splash()
        self.setWindowTitle(self.title + ' - {} [*]'.format(self.active_project.name))
        # self.setWindowModified(True)
        self.show()

    def show_splash(self):
        splash = SplashScreen()
        if splash.exec_():
            self.active_project = splash.project
            self.update_project()
            print("selected a project")
        else:
            print("Exiting program")
            sys.exit(0)



    def init_plot(self):
        """Initialize plot object, allowing us to reset/clear the workspace for new data imports"""
        # Initialize dictionary keyed by axes index with empty list to store curve channels
        self.plot_curves = {x: [] for x in range(len(self.plotter))}
        self.active_plot = 0
        self.draw_plot()

    def init_slots(self):
        """Initialize PyQt Signals/Slots for UI Buttons and Menus"""

        # File Menu Actions #
        self.actionExit.triggered.connect(self.exit)
        self.action_file_new.triggered.connect(self.new_project)
        self.action_file_open.triggered.connect(self.open_project)
        self.action_file_save.triggered.connect(self.save_project)

        # Project Menu Actions #
        self.action_import_data.triggered.connect(self.import_data)
        self.action_add_flight.triggered.connect(self.add_flight)

        # Plot Tool Actions #
        self.drawPlot_btn.clicked.connect(self.draw_plot)
        # self.clearPlot_btn.clicked.connect(self.plotter.clear)

        # Project Tree View Actions #
        self.prj_tree.doubleClicked.connect(self.log_tree)

        # Project Control Buttons #
        self.prj_add_flight.clicked.connect(self.add_flight)
        self.prj_import_data.clicked.connect(self.import_data)


        # Channel Panel Buttons #
        self.selectAllChannels.clicked.connect(self.set_channel_state)
        self.list_channels.itemChanged.connect(self.recalc_plots)
        self.resample_value.valueChanged.connect(self.draw_plot)

    def exit(self):
        """Exit the PyQt application by closing the main window (self)"""
        self.close()

    # TODO: Delete after testing
    def log_tree(self, index: QtCore.QModelIndex):
        item = self.prj_tree.model().itemFromIndex(index)
        print(item.text())
        print(dir(item))

    def log(self, text):
        """Log a message to the GUI console"""
        self.textEdit.append(str(text))

    def resample_rate(self):
        ms = self.resample_value.value() * 100
        return "{}ms".format(ms)

    def draw_plot(self, *args):
        # TODO: Figure out a way to allow redrawing of all plots at once
        if self.grav_data is not None:
            checked = self.get_selected_channels()
            series = [self.grav_data[x] for x in checked]
            self.plotter._resample = self.resample_rate()
            self.plotter.linear_plot2(self.active_plot, *series)
        else:
            self.log("Nothing to plot")

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
        print("Setting state to {}, channel is {}".format(state, channel))
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
                self.log('Error importing Gravity data file')
            else:
                # Set up the channel list for each column in gravity data
                self.set_channel_state(state=0)
                self.init_plot()  # Reinitialize plot to clear old data
                self.log('Data file loaded')
                self.prj_info.append("File path:\n{}".format(path))
                self.list_channels.clear()
                for col in self.grav_data.columns:
                    item = QtWidgets.QListWidgetItem(str(col))
                    item.setCheckState(QtCore.Qt.Unchecked)
                    self.list_channels.addItem(item)
                self.set_channel_state('gravity')

                self.log(str(self.grav_data.describe()))

    def import_data(self):
        dialog = ImportData(self.active_project)
        if dialog.exec_():
            path, dtype, flt_id = dialog.content
            if self.active_project is not None:
                flight = self.active_project.get_flight(flt_id)
                self.log("Importing {} file from {} into flight: {}".format(dtype, path, flight.uid))
            else:
                flight = None
            if self.active_project is not None:
                self.loader.load_file(path, dtype, flight, self.active_project.add_data)
                self.loader.add_hook(self.update_project)
            else:
                self.log("No active project, not importing.")

            # gps_fields = ['mdy', 'hms', 'lat', 'lon', 'ell_ht', 'ortho_ht', 'num_sats', 'pdop']
            # self.gps_data = ti.import_trajectory(path, columns=gps_fields, skiprows=1)

    def new_project(self):
        dialog = CreateProject()
        if dialog.exec_():
            name, path, prtype, desc = dialog.content
            self.log("Creating new project")
            self.active_project = prj.AirborneProject(path, name, desc)
            self.active_project.save()
            self.log(str(self.active_project))
            self.update_project()
        else:
            print("Dialog cancelled")
            return

    def open_project(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Open Project Directory", os.path.abspath('..'))
        if not path:
            return

        pattern = re.compile(r'[a-zA-Z0-9]+\.d2p')
        files = [file.name for file in os.scandir(path) if file.is_file()]
        for file in files:
            if re.match(pattern, file):
                self.log("Loading project file: {}".format(file))
                self.active_project = prj.AirborneProject.load(os.path.normpath(os.path.join(path, file)))
                self.update_project()
                return
        self.log("Project file could not be located in directory: {}".format(path))

    def update_project(self, save=False):
        print("Update project called")
        if self.active_project is None:
            return
        self.prj_tree.setModel(self.active_project.generate_model())
        self.prj_tree.expandAll()
        if save:
            self.active_project.save()

    def save_project(self):
        if self.active_project is None:
            return
        if self.active_project.save():
            self.log("Project saved.")
        else:
            self.log("Error saving project.")

    # TODO: Add decorator that will call update_project for functions that affect project structure
    def add_flight(self):
        if self.active_project is None:
            return
        meter = prj.AT1Meter('AT1M-Test')
        flight = prj.Flight(meter)
        self.active_project.add_flight(flight)
        self.update_project(save=True)


class ImportData(QtWidgets.QDialog, data_dialog):
    """

    Rationalization:
    This dialog will be used to import gravity and/or GPS data.
    A drop down box will be populated with the available project flights into which the data will be associated
    User will specify wheter the data is a gravity or gps file (TODO: maybe we can programatically determine the type)
    User will specify file path
        Maybe we can dynamically load the first 5 or so lines of data and display column headings, which would allow user
        to change the headers if necesarry
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
        print(self.dtype)
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

        # Initialize empty field values to be set on creation
        self.prj_type = None
        self.name = None
        self.path = None
        self.description = None

        # Populate the type selection list
        dgsairborne = Qt.QListWidgetItem(Qt.QIcon(':images/assets/flight_icon.png'), 'DGS Airborne', self.prj_type_list)
        # dgsairborne.setSelected(True)
        self.prj_type_list.setCurrentItem(dgsairborne)
        Qt.QListWidgetItem(Qt.QIcon(':images/assets/boat_icon.png'), 'DGS Marine', self.prj_type_list)

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

        self.name = self.prj_name.text()
        self.path = self.prj_dir.text()
        self.description = self.prj_description.toPlainText()
        self.prj_type = self.prj_type_list.currentItem().text()
        self.accept()

    def select_dir(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if path:
            self.prj_dir.setText(path)
            print("Project dir: {}".format(path))

    @property
    def content(self):
        return self.name, self.path, self.prj_type, self.description


class SplashScreen(QtWidgets.QDialog, splash_screen):
    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)

        self.dialog_buttons.accepted.connect(self.accept)
        self.btn_newproject.clicked.connect(self.new_project)
        self.btn_browse.clicked.connect(self.open_project)

        self.project = None

        self.show()

    def new_project(self):
        prj_dialog = CreateProject()
        if prj_dialog.exec_():
            name, path, prtype, desc = prj_dialog.content
            self.project = prj.AirborneProject(path, name, desc)
            self.project.save()
            # self.update()  # Update recent project lists and set it to selected

    def open_project(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if not path:
            return

        pattern = re.compile(r'[a-zA-Z0-9]+\.d2p')
        files = [file.name for file in os.scandir(path) if file.is_file()]
        for file in files:
            if re.match(pattern, file):
                self.project = prj.AirborneProject.load(os.path.normpath(os.path.join(path, file)))
                return



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    form = MainWindow()
    sys.exit(app.exec_())
