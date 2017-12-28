# coding: utf-8

import os
import io
import logging
import datetime
import pathlib
from typing import Union, List

import PyQt5.Qt as Qt
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.uic import loadUiType

import dgp.lib.project as prj
import dgp.lib.enums as enums
import dgp.lib.gravity_ingestor as gi
import dgp.lib.trajectory_ingestor as ti
from dgp.gui.models import TableModel, TableModel2, ComboEditDelegate
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
    """
    BaseDialog is an attempt to standardize some common features in the
    program dialogs.
    Currently this class provides a standard logging interface - allowing the
    programmer to send logging messages to a GUI receiver (any widget with a
    setText method) via the self.log attribute
    """

    def __init__(self, msg_recvr: str=None, parent=None, flags=0):
        super().__init__(parent=parent, flags=flags | Qt.Qt.Dialog)
        self._log = logging.getLogger(self.__class__.__name__)
        self._target = msg_recvr

    @property
    def log(self):
        return self._log

    @property
    def msg_target(self) -> QtWidgets.QWidget:
        """
        Raises
        ------
        AttributeError:
            Raised if target is invalid attribute of the UI class.

        Returns
        -------
        QWidget

        """
        return self.__getattribute__(self._target)

    def color_label(self, lbl_txt, color='red'):
        """
        Locate and highlight a label in this dialog, searching first by the
        label attribute name, then by performing a slower text matching
        iterative search through all objects in the dialog.

        Parameters
        ----------
        lbl_txt
        color

        """
        try:
            lbl = self.__getattribute__(lbl_txt)
            lbl.setStyleSheet('color: {}'.format(color))
        except AttributeError:
            for k, v in self.__dict__.items():
                if not isinstance(v, QtWidgets.QLabel):
                    continue
                if v.text() == lbl_txt:
                    v.setStyleSheet('color: {}'.format(color))

    def show_message(self, message, buddy_label=None, log=None, hl_color='red',
                     msg_color='black', target=None):
        """

        Parameters
        ----------
        message : str
            Message to display in dialog msg_target Widget, or specified target
        buddy_label : str, Optional
            Specify a label containing *buddy_label* text that should be
            highlighted in relation to this message. e.g. When warning user
            that a TextEdit box has not been filled, pass the name of the
            associated label to turn it red to draw attention.
        log : int, Optional
            Optional, log the supplied message to the logging provider at the
            given logging level (int or logging module constant)
        hl_color : str, Optional
            Optional ovveride color to highlight buddy_label with, defaults red
        msg_color : str, Optional
            Optional ovveride color to display message with
        target : str, Optional
            Send the message to the target specified here instead of any
            target specified at class instantiation.

        """
        if log is not None:
            self.log.log(level=log, msg=message)

        if target is None:
            target = self.msg_target
        else:
            target = self.__getattribute__(target)

        try:
            target.setText(message)
            target.setStyleSheet('color: {clr}'.format(clr=msg_color))
        except AttributeError:
            self.log.error("Invalid target for show_message, must support "
                           "setText attribute.")

        if buddy_label is not None:
            self.color_label(buddy_label, color=hl_color)

    def show_error(self, message):
        """Logs and displays error message in error dialog box"""
        self.log.error(message)
        dlg = QtWidgets.QMessageBox(parent=self)
        dlg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        dlg.setText(message)
        dlg.setIcon(QtWidgets.QMessageBox.Critical)
        dlg.exec_()

    def validate_not_empty(self, terminator='*'):
        """Validate that any labels with Widget buddies are not empty e.g.
        QLineEdit fields.
        Labels are only checked if their text value ends with the terminator,
        default '*'

        If any widgets are empty, the label buddy attribute names are
        returned in a list.
        """


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


class EditImportView(BaseDialog, edit_view):
    """
    Take lines of data with corresponding fields and populate custom Table Model
    Fields can be exchanged via a custom Selection Delegate, which provides a
    drop-down combobox of available fields.

    Parameters
    ----------
    data

    dtype

    parent

    """
    def __init__(self, data, dtype, parent=None):
        flags = Qt.Qt.FramelessWindowHint
        super().__init__('label_msg', parent=parent, flags=flags)
        self.setupUi(self)
        self._base_h = self.height()
        self._base_w = self.width()

        self._view = self.table_col_edit  # type: QtWidgets.QTableView
        self._view.setContextMenuPolicy(Qt.Qt.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._view_context_menu)

        self._model = None

        # Set up Field Set selection QComboBox
        self._cfs = self.cob_field_set  # type: QtWidgets.QComboBox
        if dtype == enums.DataTypes.TRAJECTORY:
            for fset in enums.GPSFields:
                self._cfs.addItem(str(fset.name).upper(), fset)
        self._cfs.currentIndexChanged.connect(self._fset_changed)

        self._setup_model(data, self._cfs.currentData().value)
        self.btn_reset.clicked.connect(
            lambda: self._setup_model(data, self._cfs.currentData().value))

    @property
    def columns(self):
        return self.model.header_row()

    @property
    def model(self) -> TableModel2:
        return self._model

    def accept(self):
        self.show_error("Test Error")
        super().accept()

    def _view_context_menu(self, point: Qt.QPoint):
        row = self._view.rowAt(point.y())
        col = self._view.columnAt(point.x())
        if -1 < col < self._view.model().columnCount() and row == 0:
            menu = QtWidgets.QMenu()
            action = QtWidgets.QAction("Custom Value", parent=menu)
            action.triggered.connect(
                lambda: print("Value is: ", self.model.value_at(row, col)))
            menu.addAction(action)
            menu.exec_(self._view.mapToGlobal(point))

    def _fset_changed(self, index):
        curr_fset = self._cfs.currentData().value
        self._view.model().set_row(0, curr_fset)

    def _setup_model(self, data, field_set: set):
        delegate = ComboEditDelegate()

        header = list(field_set)
        # TODO: Data needs to be sanitized at some stage for \n and whitespace
        while len(header) < len(data[0]):
            header.append('<None>')

        dcopy = [header]
        dcopy.extend(data)

        model = TableModel2(dcopy)

        self._view.setModel(model)
        self._view.setItemDelegate(delegate)
        self._view.resizeColumnsToContents()

        # Resize dialog to fit sample dataset
        width = self._base_w
        for idx in range(model.columnCount()):
            width += self._view.columnWidth(idx)

        height = self._base_h - 75
        for idx in range(model.rowCount()):
            height += self._view.rowHeight(idx)

        self._model = model
        self.resize(self.width(), height)


class AdvancedImport(BaseDialog, advanced_import):
    """

    Parameters
    ----------
    project : GravityProject
        Parent project
    flight : Flight
        Currently selected flight when Import button was clicked
    dtype : dgp.lib.enums.DataTypes

    parent : QWidget
        Parent Widget
    """
    def __init__(self, project, flight, dtype=None, parent=None):
        super().__init__(msg_recvr='label_msg', parent=parent)
        self.setupUi(self)

        self._preview_limit = 5
        self._path = None
        self._flight = flight
        self._cols = None
        if dtype is None:
            self._dtype = enums.DataTypes.GRAVITY
        else:
            self._dtype = dtype
        print("Initialized with dtype: ", self._dtype)

        self._file_filter = "(*.csv *.dat *.txt)"
        self._base_dir = '.'
        self._sample = None
        self.setWindowTitle("Import {}".format(dtype.name.capitalize()))

        for flt in project.flights:
            self.combo_flights.addItem(flt.name, flt)
            # scroll to this item if it matches self.flight
            if flt == self._flight:
                self.combo_flights.setCurrentIndex(self.combo_flights.count()-1)

        # Signals/Slots
        self.btn_browse.clicked.connect(self.browse)
        self.btn_edit_cols.clicked.connect(self._edit_cols)

        self.browse()

    @property
    def content(self) -> (str, str, List, prj.Flight):
        return self._path, self._dtype.name, self._cols, self._flight

    @property
    def path(self):
        return self._path

    # TODO: Data verification (basic check that values exist?)
    def accept(self) -> None:
        if self._path is None:
            self.show_message("Path cannot be empty", 'Path*')
        else:
            self._flight = self.combo_flights.currentData()
            super().accept()
        return

    def _edit_cols(self):
        if self.path is None:
            # This shouldn't happen as the button should be disabled
            self.show_message("Path cannot be empty", 'Path*',
                              log=logging.WARNING)
            return

        data = []
        with open(self.path, mode='r') as fd:
            for i, line in enumerate(fd):
                line = str(line).rstrip()
                data.append(line.split(','))
                if i == self._preview_limit:
                    break

        dlg = EditImportView(data, dtype=self._dtype, parent=self)

        if dlg.exec_():
            self._cols = dlg.columns
            self.show_message("Data Columns Updated", msg_color='Brown')

    def browse(self):
        title = "Select {typ} Data File".format(typ=self._dtype.name)
        filt = "{typ} Data {ffilt}".format(typ=self._dtype.name,
                                           ffilt=self._file_filter)
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, caption=title, directory=self._base_dir, filter=filt,
            options=QtWidgets.QFileDialog.ReadOnly)
        if not path:
            return

        self.line_path.setText(str(path))
        self._path = path
        st_size_mib = os.stat(path).st_size / 1048576
        self.field_fsize.setText("{:.3f} MiB".format(st_size_mib))

        count = 0
        sbuf = io.StringIO()
        with open(path) as fd:
            data = [fd.readline() for _ in range(self._preview_limit)]
            count += self._preview_limit

            last_line = None
            for line in fd:
                count += 1
                last_line = line

            data.append(last_line)
            print(data)

        col_count = len(data[0].split(','))
        self.field_col_count.setText(str(col_count))

        sbuf.writelines(data)
        sbuf.seek(0)

        df = None
        if self._dtype == enums.DataTypes.GRAVITY:
            df = gi.read_at1a(sbuf)
        elif self._dtype == enums.DataTypes.TRAJECTORY:
            # TODO: Implement this
            pass
            # df = ti.import_trajectory(sbuf, )

        print("Ingested df: ")
        if df is not None: print(df)

        self.field_line_count.setText("{}".format(count))
        self.btn_edit_cols.setEnabled(True)


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


class CreateProject(BaseDialog, project_dialog):
    def __init__(self, *args):
        super().__init__(msg_recvr='label_msg', *args)
        self.setupUi(self)

        self._project = None

        self.prj_browse.clicked.connect(self.select_dir)
        desktop = pathlib.Path().home().joinpath('Desktop')
        self.prj_dir.setText(str(desktop))

        # Populate the type selection list
        flt_icon = Qt.QIcon(':images/assets/flight_icon.png')
        boat_icon = Qt.QIcon(':images/assets/boat_icon.png')
        dgs_airborne = Qt.QListWidgetItem(flt_icon, 'DGS Airborne',
                                          self.prj_type_list)
        dgs_airborne.setData(QtCore.Qt.UserRole, enums.ProjectTypes.AIRBORNE)
        self.prj_type_list.setCurrentItem(dgs_airborne)
        dgs_marine = Qt.QListWidgetItem(boat_icon, 'DGS Marine',
                                        self.prj_type_list)
        dgs_marine.setData(QtCore.Qt.UserRole, enums.ProjectTypes.MARINE)

    def accept(self):
        """
        Called upon 'Create' button push, do some basic validation of fields
        then accept() if required fields are filled, otherwise color the
        labels red and display a warning message.
        """

        invld_fields = []
        for attr, label in self.__dict__.items():
            if not isinstance(label, QtWidgets.QLabel):
                continue
            text = str(label.text())
            if text.endswith('*'):
                buddy = label.buddy()
                if buddy and not buddy.text():
                    label.setStyleSheet('color: red')
                    invld_fields.append(text)
                elif buddy:
                    label.setStyleSheet('color: black')

        base_path = pathlib.Path(self.prj_dir.text())
        if not base_path.exists():
            self.show_message("Invalid Directory - Does not Exist",
                              buddy_label='label_dir')
            return

        if invld_fields:
            self.show_message('Verify that all fields are filled.')
            return

        # TODO: Future implementation for Project types other than DGS AT1A
        cdata = self.prj_type_list.currentItem().data(QtCore.Qt.UserRole)
        if cdata == enums.ProjectTypes.AIRBORNE:
            name = str(self.prj_name.text()).rstrip()
            path = pathlib.Path(self.prj_dir.text()).joinpath(name)
            if not path.exists():
                path.mkdir(parents=True)
            self._project = prj.AirborneProject(path, name)
        else:
            self.show_message("Invalid Project Type (Not yet implemented)",
                              log=logging.WARNING, msg_color='red')
            return

        super().accept()

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
