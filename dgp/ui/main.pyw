
import sys

from PyQt5 import QtCore, QtWidgets
from PyQt5.uic import loadUiType

import dgp.lib.gravity_ingestor as gi
from dgp.ui.plotter import GeneralPlot
from dgp.ui.loader import GravDataImporter

form_class, base_class = loadUiType('main_window.ui')


class MainWindow(base_class, form_class):
    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)  # Set up ui within this class - which is base_class defined by .ui file

        self.log('Initializing GUI')

        self.Plot = GeneralPlot(parent=self)
        self.mpl_toolbar = GeneralPlot.get_toolbar(self.Plot, parent=self)
        self.plotLayout.addWidget(self.Plot)
        self.plotLayout.addWidget(self.mpl_toolbar)

        self.init_slots()

        self.import_base_path = "C:\\Users\\bradyzp\\OneDrive\\Dev\\DGS\\DGP\\tests"
        self.grav_file = None
        self.grav_data = None

        self.log('GUI Initialized')

    def init_slots(self):
        """Initialize PyQt Signals/Slots for UI Buttons and Menus"""

        # Menu Actions #
        self.actionGravity_Data.triggered.connect(self.import_gravity)
        self.actionExit.triggered.connect(self.exit)

        # Plot Tool Actions #
        self.drawPlot_btn.clicked.connect(self.draw_plot)
        self.clearPlot_btn.clicked.connect(self.Plot.clear)

    def exit(self):
        """Exit the PyQt application by closing the main window (self)"""
        self.close()

    def log(self, text):
        """Log a message to the GUI console"""
        self.textEdit.append(str(text))

    def draw_plot(self):
        self.log('Plotting stuff on plotter')
        if self.grav_data is not None:
            self.Plot.linear_plot(self.grav_data.cross, self.grav_data.long, self.grav_data.Etemp)
        else:
            self.log("Nothing to plot")

    def import_gravity(self):
        # getOpenFileName returns a tuple of (path, filter), we only need the path
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Gravity Data File",
                                                        self.import_base_path,
                                                        "Data Files (*.csv *.dat)")
        if path:
            try:
                self.grav_data = gi.read_at1m(path)
            except OSError:
                self.log('Error importing file')
            else:
                self.log('Data file loaded')
                self.log(str(self.grav_data.describe()))


class TableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent=None, *args):
        super(TableModel, self).__init__()
        self.datatable = None

    def update(self, data):
        self.datatable = data


app = QtWidgets.QApplication(sys.argv)
form = MainWindow()
form.show()
sys.exit(app.exec_())
