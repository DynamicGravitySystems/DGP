# coding: utf-8

import os
import sys

from PyQt5 import QtCore, QtWidgets, Qt
from PyQt5.uic import loadUiType

import dgp.lib.gravity_ingestor as gi
from dgp.ui.plotter import GeneralPlot

form_class, base_class = loadUiType('main_window.ui')


class MainWindow(base_class, form_class):
    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)  # Set up ui within this class - which is base_class defined by .ui file

        self.log('Initializing GUI')

        # Initialize plotter canvas
        self.plotter = GeneralPlot(parent=self)
        self.plotter.generate_subplots(2)
        self.plotter.set_focus(0)

        self.mpl_toolbar = GeneralPlot.get_toolbar(self.plotter, parent=self)
        self.plotLayout.addWidget(self.plotter)
        self.plotLayout.addWidget(self.mpl_toolbar)

        self.import_base_path = os.path.join(os.getcwd(), '../../tests')
        self.grav_file = None
        self.grav_data = None
        self.refocus_flag = False

        self.plot_curves = None
        self.active_plot = 0

        self.init_plot()
        self.init_slots()
        self.setWindowState(QtCore.Qt.WindowMaximized)

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

        # Import Menu Actions #
        self.actionGravity_Data.triggered.connect(self.import_gravity)

        # Plot Tool Actions #
        self.drawPlot_btn.clicked.connect(self.draw_plot)
        # self.clearPlot_btn.clicked.connect(self.plotter.clear)

        # Channel Panel Buttons #
        self.selectAllChannels.clicked.connect(self.set_channel_state)
        self.channelList.itemChanged.connect(self.recalc_plots)
        self.resample_value.valueChanged.connect(self.draw_plot)

    def exit(self):
        """Exit the PyQt application by closing the main window (self)"""
        self.close()

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
        # print(self.plot_curves)

    def get_selected_channels(self):
        checked = []
        for i in range(self.channelList.count()):
            cn = self.channelList.item(i)
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
            for i in range(self.channelList.count()):
                self.channelList.item(i).setCheckState(state)
            return

        for i in range(self.channelList.count()):
            if self.channelList.item(i).text() in channel:
                # TODO: check state parameter for validity
                self.channelList.item(i).setCheckState(state)
            else:
                continue

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
                self.log('Error importing file')
            else:
                self.set_channel_state(state=0)
                self.init_plot()  # Reinitialize plot to clear old data
                self.log('Data file loaded')
                self.fileInfo.append("File path:\n{}".format(path))
                self.channelList.clear()
                for col in self.grav_data.columns:
                    item = QtWidgets.QListWidgetItem(str(col))
                    item.setCheckState(QtCore.Qt.Unchecked)
                    self.channelList.addItem(item)
                self.set_channel_state('gravity')

                self.log(str(self.grav_data.describe()))


app = QtWidgets.QApplication(sys.argv)
form = MainWindow()
form.show()
sys.exit(app.exec_())
