# coding: utf-8

import os
import logging
import datetime
import pathlib
from typing import Union, List

import PyQt5.Qt as Qt
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.uic import loadUiType

import dgp.lib.project as prj
from dgp.gui.models import TableModel, SelectionDelegate
from dgp.gui.utils import ConsoleHandler, LOG_COLOR_MAP
from dgp.lib.etc import gen_uuid


data_dialog, _ = loadUiType('dgp/gui/ui/data_import_dialog.ui')
advanced_import, _ = loadUiType('dgp/gui/ui/advanced_data_import.ui')
edit_view, _ = loadUiType('dgp/gui/ui/edit_import_view.ui')
flight_dialog, _ = loadUiType('dgp/gui/ui/add_flight_dialog.ui')
project_dialog, _ = loadUiType('dgp/gui/ui/project_dialog.ui')
info_dialog, _ = loadUiType('dgp/gui/ui/info_dialog.ui')
line_label_dialog, _ = loadUiType('dgp/gui/ui/set_line_label.ui')


class BaseDialog(QtWidgets.QDialog):
    def __init__(self):
        self.log = logging.getLogger(__name__)
        error_handler = ConsoleHandler(self.write_error)
        error_handler.setFormatter(logging.Formatter('%(levelname)s: '
                                                     '%(message)s'))
        error_handler.setLevel(logging.DEBUG)
        self.log.addHandler(error_handler)
        pass


class ImportData(QtWidgets.QDialog, data_dialog):
    """
    Rationalization:
    This dialog will be used to import gravity and/or GPS data.
    A drop down box will be populated with the available project flights into
    which the data will be associated
    User will specify wheter the data is a gravity or gps file (TODO: maybe we
    can programatically determine the type)
    User will specify file path

    This class does not handle the actual loading of data, it only sets up the
    parameters (path, type etc) for the calling class to do the loading.
    """
    def __init__(self, project: prj.AirborneProject=None, flight:
                 prj.Flight=None, *args):
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

        for flight in project.flights:
            self.combo_flights.addItem(flight.name, flight.uid)
            # scroll to this item if it matches self.flight
            if flight == self.flight:
                self.combo_flights.setCurrentIndex(self.combo_flights.count()-1)
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
        path = pathlib.Path(self.file_model.filePath(index))
        # TODO: Verify extensions for selected files before setting below
        if path.is_file():
            self.field_path.setText(str(path.resolve()))
            self.path = path
        else:
            return

    def browse_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Data File", os.getcwd(), "Data (*.dat *.csv)")
        if path:
            self.path = pathlib.Path(path)
            self.field_path.setText(self.path.name)
            index = self.file_model.index(str(self.path.resolve()))
            self.tree_directory.scrollTo(self.file_model.index(
                str(self.path.resolve())))
            self.tree_directory.setCurrentIndex(index)

    def accept(self):
        # '&' is used to set text hints in the GUI
        self.dtype = {'G&PS Data': 'gps', '&Gravity Data': 'gravity'}.get(
            self.group_radiotype.checkedButton().text(), 'gravity')
        self.flight = self.combo_flights.currentData()
        if self.path is None:
            return
        super().accept()

    @property
    def content(self) -> (pathlib.Path, str, prj.Flight):
        return self.path, self.dtype, self.flight


class EditImportView(QtWidgets.QDialog, edit_view):
    """
    Take lines of data with corresponding fields and populate custom Table Model
    Fields can be exchanged via a custom Selection Delegate, which provides a
    drop-down combobox of available fields.
    """
    def __init__(self, data, fields, parent):
        flags = Qt.Qt.FramelessWindowHint
        super().__init__(parent=parent, flags=flags)
        self.setupUi(self)
        self._base_h = self.height()
        self._base_w = self.width()
        self._view = self.table_col_edit  # type: QtWidgets.QTableView

        self.setup_model(fields, data)
        self.btn_reset.clicked.connect(lambda: self.setup_model(fields, data))

    @property
    def columns(self):
        return self._view.model().get_row(0)

    def setup_model(self, fields, data):
        delegate = SelectionDelegate(fields)

        model = TableModel(fields, editheader=True)
        model.append(*fields)
        for line in data:
            model.append(*line)

        self._view.setModel(model)
        self._view.setItemDelegate(delegate)
        self._view.resizeColumnsToContents()

        width = self._base_w
        for idx in range(model.columnCount()):
            width += self._view.columnWidth(idx)

        height = self._base_h - 100
        for idx in range(model.rowCount()):
            height += self._view.rowHeight(idx)

        self.resize(self.width(), height)


class AdvancedImport(QtWidgets.QDialog, advanced_import):
    def __init__(self, project, flight, dtype='gravity', parent=None):
        """

        Parameters
        ----------
        project : GravityProject
            Parent project
        flight : Flight
            Currently selected flight when Import button was clicked
        parent : QWidget
            Parent Widget
        """
        super().__init__(parent=parent)
        self.setupUi(self)
        self._preview_limit = 5
        # self._project = project
        self._path = None
        self._flight = flight
        self._cols = None
        self._dtype = dtype
        self.setWindowTitle("Import {}".format(dtype.capitalize()))

        for flt in project.flights:
            self.combo_flights.addItem(flt.name, flt)
            # scroll to this item if it matches self.flight
            if flt == self._flight:
                self.combo_flights.setCurrentIndex(self.combo_flights.count()-1)

        # Signals/Slots
        self.btn_browse.clicked.connect(self.browse_file)
        self.btn_edit_cols.clicked.connect(self._edit_cols)

        self.browse_file()

    @property
    def content(self) -> (str, str, List, prj.Flight):
        return self._path, self._dtype, self._cols, self._flight

    @property
    def path(self):
        return self._path

    def accept(self) -> None:
        self._flight = self.combo_flights.currentData()
        super().accept()
        return

    def _edit_cols(self):
        if self.path is None:
            return

        lines = []
        with open(self.path, mode='r') as fd:
            for i, line in enumerate(fd):
                lines.append(line.split(','))
                if i == self._preview_limit:
                    break

        if self._cols is not None:
            fields = self._cols
        elif self._dtype == 'gravity':
            fields = ['gravity', 'long', 'cross', 'beam', 'temp', 'status',
                      'pressure', 'Etemp', 'GPSweek', 'GPSweekseconds']
        elif self._dtype == 'gps':
            fields = ['mdy', 'hms', 'lat', 'long', 'ell_ht']
        else:
            fields = []

        dlg = EditImportView(lines, fields=fields, parent=self)

        if dlg.exec_():
            self._cols = dlg.columns
            print("Columns from edit: {}".format(self._cols))

    def browse_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select {} Data File".format(self._dtype.capitalize()),
            os.getcwd(), "Data (*.dat *.csv *.txt)")
        if path:
            self.line_path.setText(str(path))
            self._path = path
            stats = os.stat(path)
            self.label_fsize.setText("{:.3f} MiB".format(stats.st_size/1048576))
            lines = 0
            with open(path) as fd:
                for _ in fd:
                    lines += 1
            self.field_line_count.setText("{}".format(lines))


class AddFlight(QtWidgets.QDialog, flight_dialog):
    def __init__(self, project, *args):
        super().__init__(*args)
        self.setupUi(self)
        self._project = project
        self._flight = None
        self._grav_path = None
        self._gps_path = None
        self.combo_meter.addItems(project.meters)
        # self.browse_gravity.clicked.connect(functools.partial(self.browse,
        # field=self.path_gravity))
        self.browse_gravity.clicked.connect(lambda: self.browse(
            field=self.path_gravity))
        # self.browse_gps.clicked.connect(functools.partial(self.browse,
        # field=self.path_gps))
        self.browse_gps.clicked.connect(lambda: self.browse(
            field=self.path_gps))
        self.date_flight.setDate(datetime.datetime.today())
        self._uid = gen_uuid('f')
        self.text_uuid.setText(self._uid)

        self.params_model = TableModel(['Key', 'Start Value', 'End Value'],
                                       editable=[1, 2])
        self.params_model.append('Tie Location')
        self.params_model.append('Tie Reading')
        self.flight_params.setModel(self.params_model)

    def accept(self):
        qdate = self.date_flight.date()  # type: QtCore.QDate
        date = datetime.date(qdate.year(), qdate.month(), qdate.day())
        self._grav_path = self.path_gravity.text()
        self._gps_path = self.path_gps.text()
        self._flight = prj.Flight(self._project, self.text_name.text(),
                                  self._project.get_meter(
            self.combo_meter.currentText()), uuid=self._uid, date=date)
        # print(self.params_model.updates)
        super().accept()

    def browse(self, field):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Data File", os.getcwd(), "Data (*.dat *.csv *.txt)")
        if path:
            field.setText(path)

    @property
    def flight(self):
        return self._flight

    @property
    def gps(self):
        if self._gps_path is not None and len(self._gps_path) > 0:
            return pathlib.Path(self._gps_path)
        return None

    @property
    def gravity(self):
        if self._grav_path is not None and len(self._grav_path) > 0:
            return pathlib.Path(self._grav_path)
        return None


class CreateProject(QtWidgets.QDialog, project_dialog):
    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)

        self.log = logging.getLogger(__name__)
        error_handler = ConsoleHandler(self.write_error)
        error_handler.setFormatter(logging.Formatter('%(levelname)s: '
                                                     '%(message)s'))
        error_handler.setLevel(logging.DEBUG)
        self.log.addHandler(error_handler)

        self.prj_create.clicked.connect(self.create_project)
        self.prj_browse.clicked.connect(self.select_dir)
        desktop = pathlib.Path().home().joinpath('Desktop')
        self.prj_dir.setText(str(desktop))

        self._project = None

        # Populate the type selection list
        flt_icon = Qt.QIcon(':images/assets/flight_icon.png')
        boat_icon = Qt.QIcon(':images/assets/boat_icon.png')
        dgs_airborne = Qt.QListWidgetItem(flt_icon, 'DGS Airborne',
                                          self.prj_type_list)
        dgs_airborne.setData(QtCore.Qt.UserRole, 'dgs_airborne')
        self.prj_type_list.setCurrentItem(dgs_airborne)
        dgs_marine = Qt.QListWidgetItem(boat_icon, 'DGS Marine',
                                        self.prj_type_list)
        dgs_marine.setData(QtCore.Qt.UserRole, 'dgs_marine')

    def write_error(self, msg, level=None) -> None:
        self.label_required.setText(msg)
        self.label_required.setStyleSheet('color: ' + LOG_COLOR_MAP[level])

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
                self.__getattribute__(required_fields[attr]).setStyleSheet(
                    'color: red')
                invalid_input = True
            else:
                self.__getattribute__(required_fields[attr]).setStyleSheet(
                    'color: black')

        if not pathlib.Path(self.prj_dir.text()).exists():
            invalid_input = True
            self.label_dir.setStyleSheet('color: red')
            self.log.error("Invalid Directory")

        if invalid_input:
            return

        if self.prj_type_list.currentItem().data(QtCore.Qt.UserRole) == 'dgs_airborne':
            name = str(self.prj_name.text()).rstrip()
            path = pathlib.Path(self.prj_dir.text()).joinpath(name)
            if not path.exists():
                path.mkdir(parents=True)
            self._project = prj.AirborneProject(path, name)
        else:
            self.log.error("Invalid Project Type (Not Implemented)")
            return

        self.accept()

    def select_dir(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Project Parent Directory")
        if path:
            self.prj_dir.setText(path)

    @property
    def project(self):
        return self._project


class InfoDialog(QtWidgets.QDialog, info_dialog):
    def __init__(self, model, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.setupUi(self)
        self._model = model
        self.setModel(self._model)
        self.updates = None

    def setModel(self, model: QtCore.QAbstractTableModel):
        table = self.table_info  # type: QtWidgets.QTableView
        table.setModel(model)
        table.resizeColumnsToContents()
        width = 50
        for col_idx in range(model.columnCount()):
            width += table.columnWidth(col_idx)
        self.resize(width, self.height())

    def accept(self):
        self.updates = self._model.updates
        super().accept()


class SetLineLabelDialog(QtWidgets.QDialog, line_label_dialog):
    def __init__(self, label):
        super().__init__()
        self.setupUi(self)

        self._label = label

        if self._label is not None:
            self.label_txt.setText(self._label)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def accept(self):
        text = self.label_txt.text().strip()
        if text:
            self._label = text
        else:
            self._label = None
        super().accept()

    def reject(self):
        super().reject()

    @property
    def label_text(self):
        return self._label
