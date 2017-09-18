# coding: utf-8

import os
import sys
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, Union

from PyQt5 import Qt, QtWidgets, QtCore
from PyQt5.uic import loadUiType

import dgp.lib.project as prj


data_dialog, _ = loadUiType('dgp/gui/ui/data_import_dialog.ui')
flight_dialog, _ = loadUiType('dgp/gui/ui/add_flight_dialog.ui')
project_dialog, _ = loadUiType('dgp/gui/ui/project_dialog.ui')
info_dialog, _ = loadUiType('dgp/gui/ui/info_dialog.ui')


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
        self.buttonBox.accepted.connect(self.accept)

        dgsico = Qt.QIcon(':images/assets/geoid_icon.png')

        self.setWindowIcon(dgsico)
        self.path = None
        self.dtype = None
        self.flight = flight

        for flight in project:
            # TODO: Change dict index to human readable value
            self.combo_flights.addItem(flight.name, flight.uid)
            if flight == self.flight:  # scroll to this item if it matches self.flight
                self.combo_flights.setCurrentIndex(self.combo_flights.count() - 1)
        for meter in project.meters:
            self.combo_meters.addItem(meter.name)

        self.file_model = Qt.QFileSystemModel()
        self.init_tree()

    def init_tree(self):
        self.file_model.setRootPath(os.getcwd())
        self.file_model.setNameFilters(["*.csv", "*.dat"])

        self.tree_directory.setModel(self.file_model)
        self.tree_directory.scrollTo(self.file_model.index(os.getcwd()))

        self.tree_directory.resizeColumnToContents(0)
        for i in range(1, 4):  # Remove size/date/type columns from view
            self.tree_directory.hideColumn(i)
        self.tree_directory.clicked.connect(self.select_tree_file)

    def select_tree_file(self, index):
        path = Path(self.file_model.filePath(index))
        # TODO: Verify extensions for selected files before setting below
        if path.is_file():
            self.field_path.setText(os.path.normpath(path))  # TODO: Change this to use pathlib function
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

    def accept(self):
        # '&' is used to set text hints in the GUI
        self.dtype = {'G&PS Data': 'gps', '&Gravity Data': 'gravity'}.get(self.group_radiotype.checkedButton().text(),
                                                                          'gravity')
        self.flight = self.combo_flights.currentData()
        if self.path is None:
            return
        super().accept()

    @property
    def content(self) -> (Path, str, prj.Flight):
        return self.path, self.dtype, self.flight


class AddFlight(QtWidgets.QDialog, flight_dialog):
    def __init__(self, project, *args):
        super().__init__(*args)
        self.setupUi(self)
        self._project = project
        self._flight = None
        self.combo_meter.addItems(project.meters)
        self.date_flight.setDate(datetime.datetime.today())
        self._uid = prj.Flight.generate_uuid()
        self.text_uuid.setText(self._uid)

    def accept(self):
        qdate = self.date_flight.date()  # type: QtCore.QDate
        date = datetime.date(qdate.year(), qdate.month(), qdate.day())
        self._flight = prj.Flight(self._project, self.text_name.text(), self._project.get_meter(
            self.combo_meter.currentText()), uuid=self._uid, date=date)
        super().accept()

    @property
    def flight(self):
        return self._flight


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


class InfoDialog(QtWidgets.QDialog, info_dialog):
    def __init__(self, model, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.setupUi(self)
        self.setModel(model)

    def setModel(self, model):
        table = self.table_info  # type: QtWidgets.QTableView
        table.setModel(model)
        table.resizeColumnsToContents()
        width = 50
        for col_idx in range(table.colorCount()):
            width += table.columnWidth(col_idx)
        self.resize(width, self.height())


class InfoModel(QtCore.QAbstractTableModel):
    """Simple table model of key: value pairs."""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # A list of 2-tuples (key: value pairs) which will be the table rows
        self._data = []

    def set_object(self, obj):
        """Populates the model with key, value pairs from the passed objects' __dict__"""
        for key, value in obj.__dict__.items():
            self.add_row(key, value)

    def add_row(self, key, value):
        self._data.append((str(key), repr(value)))

    # Required implementations of super class (for a basic, non-editable table)

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self._data)

    def columnCount(self, parent=None, *args, **kwargs):
        return 2

    def data(self, index: QtCore.QModelIndex, role=None):
        if role == QtCore.Qt.DisplayRole:
            return self._data[index.row()][index.column()]
        return QtCore.QVariant()

    def flags(self, index: QtCore.QModelIndex):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def headerData(self, section, orientation, role=None):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return ['Key', 'Value'][section]
