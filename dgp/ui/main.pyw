
import sys

from PyQt5 import QtCore, QtWidgets, Qt
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

        self.plotter = GeneralPlot(parent=self)
        self.plotter.generate_subplots(2)
        print(self.plotter.axes)
        self.mpl_toolbar = GeneralPlot.get_toolbar(self.plotter, parent=self)
        self.plotLayout.addWidget(self.plotter)
        self.plotLayout.addWidget(self.mpl_toolbar)

        self.init_slots()

        self.import_base_path = "C:\\Users\\bradyzp\\OneDrive\\Dev\\DGS\\DGP\\test"
        self.grav_file = None
        self.grav_data = None

        self.active_plot = 0

    def init_slots(self):
        """Initialize PyQt Signals/Slots for UI Buttons and Menus"""

        # File Menu Actions #
        self.actionExit.triggered.connect(self.exit)

        # Import Menu Actions #
        self.actionGravity_Data.triggered.connect(self.import_gravity)

        # Plot Tool Actions #
        self.drawPlot_btn.clicked.connect(self.draw_plot)
        self.clearPlot_btn.clicked.connect(self.plotter.clear)

        # Channel Panel Buttons #
        self.selectAllChannels.clicked.connect(self.select_all_channels)

    def exit(self):
        """Exit the PyQt application by closing the main window (self)"""
        self.close()

    def log(self, text):
        """Log a message to the GUI console"""
        self.textEdit.append(str(text))

    def draw_plot(self):
        self.log('Plotting stuff on plotter')
        if self.grav_data is not None:
            checked = self.get_selected_channels()
            series = [self.grav_data[x] for x in checked]
            self.plotter.linear_plot(self.active_plot, *series)
        else:
            self.log("Nothing to plot")

    def select_all_channels(self):
        for i in range(self.channelList.count()):
            self.channelList.item(i).setCheckState(2)  # Qt::CheckState 2 = checked 1 = partially checked

    def get_selected_channels(self):
        checked = []
        for i in range(self.channelList.count()):
            cn = self.channelList.item(i)
            if cn.checkState():
                checked.append(cn.text())
        return checked

    def set_channels(self):
        if self.grav_data is not None:
            for col in self.grav_data.columns:
                item = QtWidgets.QListWidgetItem(str(col))
                item.setCheckState(QtCore.Qt.Unchecked)
                self.channelList.addItem(item)
        else:
            return

    def set_file_info(self, path):
        self.fileInfo.append("File path:\n{}".format(path))

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
                self.set_file_info(path)
                self.set_channels()
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
