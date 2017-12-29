# coding: utf-8

import os
import io
import logging
import datetime
import pathlib

import PyQt5.Qt as Qt
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.uic import loadUiType

import dgp.lib.project as prj
import dgp.lib.enums as enums
import dgp.gui.loader as qloader
from dgp.gui.models import TableModel, TableModel2, ComboEditDelegate
from dgp.lib.types import DataSource
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


class EditImportView(BaseDialog, edit_view):
    # TODO: Provide method of saving custom changes to columns between
    # re-opening of this dialog. Perhaps under custom combo-box item.
    """
    Take lines of data with corresponding fields and populate custom Table Model
    Fields can be exchanged via a custom Selection Delegate, which provides a
    drop-down combobox of available fields.

    Parameters
    ----------
    field_enum :
        An enumeration consisting of Enumerated items mapped to Field Tuples
        i.e. field_enum.AT1A.value == ('Gravity', 'long', 'cross', ...)

    parent :
        Parent Widget to this Dialog

    """
    def __init__(self, field_enum, parent=None):
        flags = Qt.Qt.Dialog
        super().__init__('label_msg', parent=parent, flags=flags)
        self.setupUi(self)
        self._base_h = self.height()
        self._base_w = self.width()
        self._fields = field_enum
        self._cfs = self.cob_field_set  # type: QtWidgets.QComboBox
        self._data = None

        # Configure the QTableView
        self._view = self.table_col_edit  # type: QtWidgets.QTableView
        self._view.setContextMenuPolicy(Qt.Qt.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._view_context_menu)

        # Configure the QComboBox for Field Set selection
        for fset in field_enum:
            self._cfs.addItem(str(fset.name).upper(), fset)

        self._cfs.currentIndexChanged.connect(lambda: self._setup_model(
            self._data, self._cfs.currentData()))
        self.btn_reset.clicked.connect(lambda: self._setup_model(
            self._data, self._cfs.currentData()))

    def exec_(self):
        if self._data is None:
            raise ValueError("Data must be set before executing dialog.")
        return super().exec_()

    def set_state(self, data, current_field=None):
        self._data = data
        self._setup_model(data, self._cfs.currentData())
        if current_field is not None:
            idx = self._cfs.findText(current_field.name,
                                     flags=Qt.Qt.MatchExactly)
            self._cfs.setCurrentIndex(idx)

    @property
    def columns(self):
        return self.model.header_row()

    @property
    def field_enum(self):
        return self._cfs.currentData()

    @property
    def model(self) -> TableModel2:
        return self._view.model()
    
    @property
    def skip_row(self) -> bool:
        """Returns value of UI's 'Has Header' CheckBox to determine if first
        row should be skipped (Header already defined in data)."""
        return self.chb_has_header.isChecked()

    def accept(self):
        super().accept()

    def _view_context_menu(self, point: Qt.QPoint):
        row = self._view.rowAt(point.y())
        col = self._view.columnAt(point.x())
        index = self.model.index(row, col)
        if -1 < col < self._view.model().columnCount() and row == 0:
            menu = QtWidgets.QMenu()
            action = QtWidgets.QAction("Custom Value", parent=menu)
            action.triggered.connect(lambda: self._custom_label(index))

            menu.addAction(action)
            menu.exec_(self._view.mapToGlobal(point))

    def _custom_label(self, index: QtCore.QModelIndex):
        # For some reason QInputDialog.getText does not recognize kwargs
        cur_val = index.data(role=QtCore.Qt.DisplayRole)
        text, ok = QtWidgets.QInputDialog.getText(self,
                                                  "Input Value",
                                                  "Input Custom Value",
                                                  text=cur_val)
        if ok:
            self.model.setData(index, text.strip())
            return

    def _setup_model(self, data, field_set):
        delegate = ComboEditDelegate()

        header = list(field_set.value)
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

        # TODO: This fixed pixel value is not ideal
        height = self._base_h - 75
        for idx in range(model.rowCount()):
            height += self._view.rowHeight(idx)

        self._model = model
        self.resize(self.width(), height)


class AdvancedImport(BaseDialog, advanced_import):
    """
    Provides a dialog for importing Trajectory or Gravity data.
    This dialog computes and displays some basic file information,
    and provides a mechanism for previewing and adjusting column headers via
    the EditImportView dialog class.

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
    data = QtCore.pyqtSignal(prj.Flight, DataSource)

    def __init__(self, project, flight, dtype=enums.DataTypes.GRAVITY,
                 parent=None):
        super().__init__(msg_recvr='label_msg', parent=parent)
        self.setupUi(self)

        self._preview_limit = 5
        self._path = None
        self._flight = flight
        self._custom_cols = None
        self._dtype = dtype

        self._file_filter = "(*.csv *.dat *.txt)"
        self._base_dir = '.'
        self._sample = None
        self.setWindowTitle("Import {}".format(dtype.name.capitalize()))

        # Establish field enum based on dtype
        self._fields = {enums.DataTypes.GRAVITY: enums.GravityTypes,
                        enums.DataTypes.TRAJECTORY: enums.GPSFields}[dtype]

        for flt in project.flights:
            self.combo_flights.addItem(flt.name, flt)
            if flt == self._flight:
                self.combo_flights.setCurrentIndex(self.combo_flights.count()-1)

        for fmt in self._fields:
            self._fmt_picker.addItem(str(fmt.name).upper(), fmt)

        # Signals/Slots
        self.btn_browse.clicked.connect(self.browse)
        self.btn_edit_cols.clicked.connect(self._edit_cols)

        self._edit_dlg = EditImportView(self._fields, parent=self)

        # Launch browse dialog immediately
        self.browse()

    @property
    def _fmt_picker(self) -> QtWidgets.QComboBox:
        return self.cb_data_fmt

    @property
    def flight(self):
        return self._flight

    @property
    def path(self):
        return self._path

    def accept(self) -> None:
        if self._path is None:
            self.show_message("Path cannot be empty", 'Path*')
            return

        # Process accept and run LoadFile threader
        self._flight = self.combo_flights.currentData()
        progress = QtWidgets.QProgressDialog(
            'Loading {pth}'.format(pth=self._path), None, 0, 0, self.parent(),
            QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint |
            QtCore.Qt.WindowMinimizeButtonHint)
        progress.setWindowTitle("Loading")

        if self._custom_cols is not None:
            cols = self._custom_cols
        else:
            cols = self._fmt_picker.currentData().value

        if self._edit_dlg.skip_row:
            skip = 1
        else:
            skip = None

        ld = qloader.LoadFile(self._path, self._dtype, cols,
                              parent=self, skiprow=skip)
        ld.data.connect(lambda ds: self.data.emit(self._flight, ds))
        ld.error.connect(lambda x: progress.close())
        ld.error.connect(self._import_error)
        ld.start()

        progress.show()
        progress.setValue(1)
        super().accept()

    def _import_error(self, error: bool):
        if not error:
            return
        self.show_error("Failed to import datafile. See log trace.")

    def _edit_cols(self):
        """Launches the EditImportView dialog to allow user to preview and
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

        # Generate sample set of data for Column editor
        data = []
        with open(self.path, mode='r') as fd:
            for i, line in enumerate(fd):
                line = str(line).rstrip()
                data.append(line.split(','))
                if i == self._preview_limit:
                    break

        # Update the edit dialog with current data
        self._edit_dlg.set_state(data, self._fmt_picker.currentData())
        if self._edit_dlg.exec_():
            selected_enum = self._edit_dlg.field_enum
            idx = self._fmt_picker.findData(selected_enum, role=Qt.Qt.UserRole)
            if idx != -1:
                self._fmt_picker.setCurrentIndex(idx)

            self.show_message("Data Columns Updated", msg_color='Green')

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

        col_count = len(data[0].split(','))
        self.field_col_count.setText(str(col_count))

        sbuf.writelines(data)
        sbuf.seek(0)

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
