# coding: utf-8

import os
import io
import csv
import types
import logging
import datetime
import pathlib
from typing import Union

import PyQt5.Qt as Qt
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.uic import loadUiType

import dgp.lib.project as prj
import dgp.lib.enums as enums
from dgp.gui.models import TableModel, ComboEditDelegate
from dgp.lib.etc import gen_uuid


data_dialog, _ = loadUiType('dgp/gui/ui/data_import_dialog.ui')
advanced_import, _ = loadUiType('dgp/gui/ui/advanced_data_import.ui')
edit_view, _ = loadUiType('dgp/gui/ui/edit_import_view.ui')
flight_dialog, _ = loadUiType('dgp/gui/ui/add_flight_dialog.ui')
project_dialog, _ = loadUiType('dgp/gui/ui/project_dialog.ui')

PATH_ERR = "Path cannot be empty."


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
                     color='black', target=None):
        """
        Displays a message in the widgets msg_target widget (any widget that
        supports setText()), as definied on initialization.
        Optionally also send the message to the dialog's logger at specified
        level, and highlights a buddy label a specified color, or red.

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
        color : str, Optional
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
            target.setStyleSheet('color: {clr}'.format(clr=color))
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
        dlg.setWindowTitle("Error")
        dlg.exec_()

    def validate_not_empty(self, terminator='*'):
        """Validate that any labels with Widget buddies are not empty e.g.
        QLineEdit fields.
        Labels are only checked if their text value ends with the terminator,
        default '*'

        If any widgets are empty, the label buddy attribute names are
        returned in a list.
        """


class EditImportDialog(BaseDialog, edit_view):
    """
    Take lines of data with corresponding fields and populate custom Table Model
    Fields can be exchanged via a custom Selection Delegate, which provides a
    drop-down combobox of available fields.

    Parameters
    ----------
    formats :
        An enumeration consisting of Enumerated items mapped to Field Tuples
        i.e. field_enum.AT1A.value == ('Gravity', 'long', 'cross', ...)
    edit_header : bool
        Allow the header row to be edited if True.
        Currently there seems to be no reason to permit editing of gravity
        data files as they are expected to be very uniform. However this is
        useful with GPS data files where we have seen some columns switched
        or missing.
    parent :
        Parent Widget to this Dialog

    """
    def __init__(self, formats, edit_header=False, parent=None):
        flags = Qt.Qt.Dialog
        super().__init__('label_msg', parent=parent, flags=flags)
        self.setupUi(self)
        self._base_h = self.height()
        self._base_w = self.width()

        # Configure the QTableView
        self._view = self.table_col_edit  # type: QtWidgets.QTableView
        self._view.setContextMenuPolicy(Qt.Qt.CustomContextMenu)
        if edit_header:
            self._view.customContextMenuRequested.connect(self._context_menu)
            self._view.setItemDelegate(ComboEditDelegate())

        for item in formats:
            name = str(item.name).upper()
            self.cb_format.addItem(name, item)

        model = TableModel(self.format.value, editable_header=edit_header)
        self._view.setModel(model)

        self.cb_format.currentIndexChanged.connect(lambda: self._set_header())
        self.btn_reset.clicked.connect(lambda: self._set_header())

    def exec_(self):
        self._autofit()
        return super().exec_()

    def _set_header(self):
        """pyQt Slot:
        Set the TableModel header row values to the current data_format values
        """
        self.model.table_header = self.format.value
        self._autofit()

    def _autofit(self):
        """Adjust dialog height/width based on table view contents"""
        self._view.resizeColumnsToContents()
        dl_width = self._base_w
        for col in range(self.model.columnCount()):
            dl_width += self._view.columnWidth(col)

        dl_height = self._base_h
        for row in range(self.model.rowCount()):
            dl_height += self._view.rowHeight(row)
            if row >= 5:
                break
        self.resize(dl_width, dl_height)

    @property
    def data(self):
        return self.model.model_data

    @data.setter
    def data(self, value):
        self.model.model_data = value

    @property
    def columns(self):
        # TODO: This is still problematic, what happens if a None column is
        # in the middle of the data set? Cols will be skewed.
        return [col for col in self.model.table_header if col != 'None']

    @property
    def cb_format(self) -> QtWidgets.QComboBox:
        return self.cob_field_set

    @property
    def format(self):
        return self.cb_format.currentData()

    @format.setter
    def format(self, value):
        if isinstance(value, str):
            idx = self.cb_format.findText(value)
        else:
            idx = self.cb_format.findData(value)
        if idx == -1:
            self.cb_format.setCurrentIndex(0)
        else:
            self.cb_format.setCurrentIndex(idx)

    @property
    def model(self) -> TableModel:
        return self._view.model()
    
    @property
    def skiprow(self) -> Union[int, None]:
        """Returns value of UI's 'Has Header' CheckBox to determine if first
        row should be skipped (Header already defined in data).
        """
        if self.chb_has_header.isChecked():
            return 1
        return None

    @skiprow.setter
    def skiprow(self, value: bool):
        self.chb_has_header.setChecked(bool(value))

    def _context_menu(self, point: Qt.QPoint):
        row = self._view.rowAt(point.y())
        col = self._view.columnAt(point.x())
        index = self.model.index(row, col)
        if -1 < col < self._view.model().columnCount() and row == 0:
            menu = QtWidgets.QMenu()
            action = QtWidgets.QAction("Custom Value")
            action.triggered.connect(lambda: self._custom_label(index))

            menu.addAction(action)
            menu.exec_(self._view.mapToGlobal(point))

    def _custom_label(self, index: QtCore.QModelIndex):
        # For some reason QInputDialog.getText does not recognize some kwargs
        cur_val = index.data(role=QtCore.Qt.DisplayRole)
        text, ok = QtWidgets.QInputDialog.getText(self,
                                                  "Input Value",
                                                  "Input Custom Value",
                                                  text=cur_val)
        if ok:
            self.model.setData(index, text.strip())
            return


class AdvancedImportDialog(BaseDialog, advanced_import):
    """
    Provides a dialog for importing Trajectory or Gravity data.
    This dialog computes and displays some basic file information,
    and provides a mechanism for previewing and adjusting column headers via
    the EditImportDialog class.

    Parameters
    ----------
    project : GravityProject
        Parent project
    flight : Flight
        Currently selected flight when Import button was clicked
    dtype : dgp.lib.enums.DataTypes
        Data type to import using this dialog, GRAVITY or TRAJECTORY
    parent : QWidget
        Parent Widget
    """

    def __init__(self, project, flight, dtype=enums.DataTypes.GRAVITY,
                 parent=None):
        super().__init__(msg_recvr='label_msg', parent=parent)
        self.setupUi(self)

        self._preview_limit = 5
        self._path = None
        self._dtype = dtype
        self._file_filter = "(*.csv *.dat *.txt)"
        self._base_dir = '.'
        self._sample = None

        icon = {enums.DataTypes.GRAVITY: ':icons/gravity',
                enums.DataTypes.TRAJECTORY: ':icons/gps'}[dtype]
        self.setWindowIcon(Qt.QIcon(icon))
        self.setWindowTitle("Import {}".format(dtype.name.capitalize()))

        # Establish field enum based on dtype
        self._fields = {enums.DataTypes.GRAVITY: enums.GravityTypes,
                        enums.DataTypes.TRAJECTORY: enums.GPSFields}[dtype]

        formats = sorted(self._fields, key=lambda x: x.name)
        for item in formats:
            name = str(item.name).upper()
            self.cb_format.addItem(name, item)

        editable = self._dtype == enums.DataTypes.TRAJECTORY
        self._editor = EditImportDialog(formats=formats,
                                        edit_header=editable,
                                        parent=self)

        for flt in project.flights:
            self.combo_flights.addItem(flt.name, flt)
        if not self.combo_flights.count():
            self.combo_flights.addItem("No Flights Available", None)

        for mtr in project.meters:
            self.combo_meters.addItem(mtr.name, mtr)
        if not self.combo_meters.count():
            self.combo_meters.addItem("No Meters Available", None)

        if flight is not None:
            flt_idx = self.combo_flights.findData(flight)
            self.combo_flights.setCurrentIndex(flt_idx)

        # Signals/Slots
        self.cb_format.currentIndexChanged.connect(
            lambda idx: self.editor.cb_format.setCurrentIndex(idx))
        self.btn_browse.clicked.connect(self.browse)
        self.btn_edit_cols.clicked.connect(self._edit)

    @property
    def params(self):
        return dict(path=self.path,
                    subtype=self.format,
                    skiprows=self.editor.skiprow,
                    columns=self.editor.columns)

    @property
    def editor(self) -> EditImportDialog:
        return self._editor

    @property
    def cb_format(self) -> QtWidgets.QComboBox:
        return self.cb_data_fmt

    @property
    def format(self):
        return self.cb_format.currentData()

    @format.setter
    def format(self, value):
        if isinstance(value, str):
            idx = self.cb_format.findText(value)
        else:
            idx = self.cb_format.findData(value)
        if idx == -1:
            self.cb_format.setCurrentIndex(0)
        else:
            self.cb_format.setCurrentIndex(idx)
            self.editor.format = value

    @property
    def flight(self):
        return self.combo_flights.currentData()

    @property
    def path(self) -> pathlib.Path:
        return self._path

    @path.setter
    def path(self, value):
        if value is None:
            self._path = None
            self.btn_edit_cols.setEnabled(False)
            self.btn_dialog.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(
                False)
            self.line_path.setText('None')
            return

        self._path = pathlib.Path(value)
        self.line_path.setText(str(self._path.resolve()))
        if not self._path.exists():
            self.log.warning(PATH_ERR)
            self.show_message(PATH_ERR, 'Path*', color='red')
            self.btn_edit_cols.setEnabled(False)
        else:
            self._update()
            self.btn_edit_cols.setEnabled(True)

    def accept(self) -> None:
        if self.path is None:
            self.show_message(PATH_ERR, 'Path*', color='red')
            return
        if self.flight is None:
            self.show_error("Must select a valid flight to import data.")
            return

        super().accept()

    def _edit(self):
        """Launches the EditImportDialog to allow user to preview and
        edit column name/position as necesarry.

        Notes
        -----
        To simplify state handling & continuity (dialog should preserve options
        and state through multiple uses), an EditImportView dialog is
        initialized in the AdvancedImport constructor, to be reused through
        the life of this dialog.

        Before re-launching the EIV dialog a call to set_state must be made
        to update the data displayed within.
        """
        if self.path is None:
            return

        # self.editor.format = self.cb_format.currentData()
        self.editor.data = self._sample

        if self.editor.exec_():
            # Change format combobox to match change in editor
            idx = self.cb_format.findData(self.editor.format)
            if idx != -1:
                self.cb_format.setCurrentIndex(idx)

            self.show_message("Data Columns Updated", color='Green')
            self.log.debug("Columns: {}".format(self.editor.columns))

    def _update(self):
        """Analyze path for statistical information/sample"""
        st_size_mib = self.path.stat().st_size / 1048576
        self.field_fsize.setText("{:.3f} MiB".format(st_size_mib))

        # Generate sample set of data for Column editor
        sample = []
        with self.path.open(mode='r', newline='') as fd:
            try:
                has_header = csv.Sniffer().has_header(fd.read(8192))
            except csv.Error:
                has_header = False
            fd.seek(0)

            # Read in sample set
            rdr = csv.reader(fd)
            count = 0
            for i, line in enumerate(rdr):
                count += 1
                if i <= self._preview_limit - 1:
                    sample.append(line)

        self.field_line_count.setText("{}".format(count))
        if has_header:
            self.show_message("Autodetected Header in File", color='green')
            self.editor.skiprow = True

        if not len(sample):
            col_count = 0
        else:
            col_count = len(sample[0])
        self.field_col_count.setText(str(col_count))

        self._sample = sample

        # count = 0
        # sbuf = io.StringIO()
        # with open(self.path) as fd:
        #     data = [fd.readline() for _ in range(self._preview_limit)]
        #     count += self._preview_limit
        #
        #     last_line = None
        #     for line in fd:
        #         count += 1
        #         last_line = line
        #     data.append(last_line)
        #
        # col_count = len(data[0].split(','))
        #
        # sbuf.writelines(data)
        # sbuf.seek(0)

        # Experimental - Read portion of data to get timestamps
        # df = None
        # if self._dtype == enums.DataTypes.GRAVITY:
        #     try:
        #         df = gi.read_at1a(sbuf)
        #     except:
        #         print("Error ingesting sample data")
        # elif self._dtype == enums.DataTypes.TRAJECTORY:
        #     # TODO: Implement this
        #     pass
        #     # df = ti.import_trajectory(sbuf, )

    def browse(self):
        title = "Select {} Data File".format(self._dtype.name.capitalize())
        filt = "{typ} Data {ffilt}".format(typ=self._dtype.name.capitalize(),
                                           ffilt=self._file_filter)
        raw_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, caption=title, directory=str(self._base_dir),
            filter=filt, options=QtWidgets.QFileDialog.ReadOnly)
        if raw_path:
            self.path = raw_path
            self._base_dir = self.path.parent
        else:
            return


class AddFlightDialog(QtWidgets.QDialog, flight_dialog):
    def __init__(self, project, *args):
        super().__init__(*args)
        self.setupUi(self)
        self._project = project
        self._flight = None
        self._grav_path = None
        self._gps_path = None
        self.combo_meter.addItems(project.meters)
        self.browse_gravity.clicked.connect(lambda: self.browse(
            field=self.path_gravity))
        self.browse_gps.clicked.connect(lambda: self.browse(
            field=self.path_gps))
        self.date_flight.setDate(datetime.datetime.today())
        self._uid = gen_uuid('f')
        self.text_uuid.setText(self._uid)

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


class CreateProjectDialog(BaseDialog, project_dialog):
    def __init__(self, *args):
        super().__init__(msg_recvr='label_msg', *args)
        self.setupUi(self)

        self._project = None

        self.prj_browse.clicked.connect(self.select_dir)
        desktop = pathlib.Path().home().joinpath('Desktop')
        self.prj_dir.setText(str(desktop))

        # Populate the type selection list
        flt_icon = Qt.QIcon(':icons/airborne')
        boat_icon = Qt.QIcon(':icons/marine')
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
                              log=logging.WARNING, color='red')
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


class PropertiesDialog(BaseDialog):
    def __init__(self, cls, parent=None):
        super().__init__(parent=parent)
        # Store label: data as dictionary
        self._data = dict()
        self.setWindowTitle('Properties')

        vlayout = QtWidgets.QVBoxLayout()
        try:
            name = cls.__getattribute__('name')
        except AttributeError:
            name = ''

        self._title = QtWidgets.QLabel('<h1>{cls}: {name}</h1>'.format(
            cls=cls.__class__.__name__, name=name))
        self._title.setAlignment(Qt.Qt.AlignHCenter)
        self._form = QtWidgets.QFormLayout()

        self._btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        self._btns.accepted.connect(self.accept)

        vlayout.addWidget(self._title, alignment=Qt.Qt.AlignTop)
        vlayout.addLayout(self._form)
        vlayout.addWidget(self._btns, alignment=Qt.Qt.AlignBottom)

        self.setLayout(vlayout)

        self.log.info("Properties Dialog Initialized")
        if cls is not None:
            self.populate_form(cls)
        self.show()

    @property
    def data(self):
        return None

    @property
    def form(self) -> QtWidgets.QFormLayout:
        return self._form

    @staticmethod
    def _is_abstract(obj):
        if hasattr(obj, '__isabstractmethod__') and obj.__isabstractmethod__:
            return True
        return False

    def _build_widget(self, value):
        if value is None:
            return QtWidgets.QLabel('None')
        if isinstance(value, str):
            return QtWidgets.QLabel(value)
        elif isinstance(value, (list, types.GeneratorType)):
            rv = QtWidgets.QVBoxLayout()
            for i, item in enumerate(value):
                if i >= 5:
                    rv.addWidget(QtWidgets.QLabel("{} More Items...".format(
                        len(value) - 5)))
                    break
                # rv.addWidget(QtWidgets.QLabel(str(item)))
                rv.addWidget(self._build_widget(item))
            return rv
        elif isinstance(value, dict):
            rv = QtWidgets.QFormLayout()
            for key, val in value.items():
                rv.addRow(str(key), self._build_widget(val))
            return rv

        else:
            return QtWidgets.QLabel(repr(value))

    def populate_form(self, instance):
        for cls in instance.__class__.__mro__:
            for binding, attr in cls.__dict__.items():
                if not self._is_abstract(attr) and isinstance(attr, property):
                    value = instance.__getattribute__(binding)
                    lbl = "<H3>{}:</H3>".format(str(binding).capitalize())
                    self.form.addRow(lbl, self._build_widget(value))
