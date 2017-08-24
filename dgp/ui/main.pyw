# coding: utf-8

import os
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

        # Initialize plotter canvas
        self.plotter = GeneralPlot(parent=self)
        self.plotter.generate_subplots(2)

        self.mpl_toolbar = GeneralPlot.get_toolbar(self.plotter, parent=self)
        self.plotLayout.addWidget(self.plotter)
        self.plotLayout.addWidget(self.mpl_toolbar)
        # Initialize dictionary keyed by axes index with empty list to store curve channels
        self.plot_curves = {x: [] for x in range(len(self.plotter))}

        self.init_slots()

        self.import_base_path = os.path.join(os.getcwd(), '../../tests')
        self.grav_file = None
        self.grav_data = None
        self.active_plot = 0
        self.refocus_flag = False


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
        self.selectAllChannels.clicked.connect(self.set_all_channels)
        self.channelList.itemChanged.connect(self.recalc_plots)

    def exit(self):
        """Exit the PyQt application by closing the main window (self)"""
        self.close()

    def log(self, text):
        """Log a message to the GUI console"""
        self.textEdit.append(str(text))

    def resample_rate(self):
        ms = self.resample_value.value() * 100
        return "{}ms".format(ms)

    def draw_plot(self):
        if self.grav_data is not None:
            checked = self.get_selected_channels()
            series = [self.grav_data[x] for x in checked]
            self.plotter.linear_plot(self.active_plot, *series, resample=self.resample_rate())
        else:
            self.log("Nothing to plot")

    def set_active_plot(self, index):
        self.refocus_flag = True
        self.active_plot = index
        self.set_all_channels(state=0)
        self.set_channel_state(*self.plot_curves[index])
        self.refocus_flag = False

    def set_all_channels(self, *args, state=2):
        for i in range(self.channelList.count()):
            self.channelList.item(i).setCheckState(state)  # Qt::CheckState 2 = checked 1 = partially checked

    def recalc_plots(self, *list_items):
        if self.refocus_flag:
            return
        for item in list_items:
            if item.checkState() == 2:
                self.plot_curves[self.active_plot].append(item.text())
            else:
                self.plot_curves[self.active_plot].remove(item.text())
        self.draw_plot()
        print(self.plot_curves)

    def set_plotted_channels(self):
        self.log("Setting checks for channels on active plot: {}".format(self.active_plot))

    def get_selected_channels(self):
        checked = []
        for i in range(self.channelList.count()):
            cn = self.channelList.item(i)
            if cn.checkState() == 2:
                checked.append(cn.text())
        return checked

    def set_channel_state(self, *channel, state=2):
        """
        Set the checked state of the specified channel
        :param channel: [(str)] channel name
        :param state: (int) QListWidgetItem CheckState value 0: unchecked 1: partially checked 2: checked
        """
        for i in range(self.channelList.count()):
            if self.channelList.item(i).text() in channel:
                # TODO: check state parameter for validity
                self.channelList.item(i).setCheckState(state)
            else:
                continue

    def set_channels(self):
        """Add channels to the channel list box based on the imported grav_data columns, clearing old ones first."""
        if self.grav_data is not None:
            self.channelList.clear()
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


app = QtWidgets.QApplication(sys.argv)
form = MainWindow()
form.show()
sys.exit(app.exec_())
