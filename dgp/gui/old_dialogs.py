# -*- coding: utf-8 -*-

import types
import logging
from typing import Union

import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtCore import Qt, QPoint, QModelIndex

from dgp.gui.models import TableModel, ComboEditDelegate

from dgp.gui.ui import edit_import_view

PATH_ERR = "Path cannot be empty."


class BaseDialog(QtWidgets.QDialog):  # pragma: no cover
    """
    BaseDialog is an attempt to standardize some common features in the
    program dialogs.
    Currently this class provides a standard logging interface - allowing the
    programmer to send logging messages to a GUI receiver (any widget with a
    setText method) via the self.log attribute
    """

    def __init__(self, msg_recvr: str = None, parent=None, flags=0):
        super().__init__(parent=parent, flags=flags | Qt.Dialog)
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

        try:
            if target is None:
                target = self.msg_target
            else:
                target = self.__getattribute__(target)
        except AttributeError:
            self.log.error("No valid target available for show_message.")
            return

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


# TODO: EditImportDialog and PropertiesDialog are deprecated - keeping them for example code currently


class EditImportDialog(BaseDialog, edit_import_view.Ui_Dialog):  # pragma: no cover
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
        flags = Qt.Dialog

        super().__init__('label_msg', parent=parent, flags=flags)
        self.setupUi(self)
        self._base_h = self.height()
        self._base_w = self.width()

        # Configure the QTableView
        self._view = self.table_col_edit  # type: QtWidgets.QTableView
        self._view.setContextMenuPolicy(Qt.CustomContextMenu)
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

    def _context_menu(self, point: QPoint):
        row = self._view.rowAt(point.y())
        col = self._view.columnAt(point.x())
        index = self.model.index(row, col)
        if -1 < col < self._view.model().columnCount() and row == 0:
            menu = QtWidgets.QMenu()
            action = QtWidgets.QAction("Custom Value")
            action.triggered.connect(lambda: self._custom_label(index))

            menu.addAction(action)
            menu.exec_(self._view.mapToGlobal(point))

    def _custom_label(self, index: QModelIndex):
        # For some reason QInputDialog.getText does not recognize some kwargs
        cur_val = index.data(role=Qt.DisplayRole)
        text, ok = QtWidgets.QInputDialog.getText(self,
                                                  "Input Value",
                                                  "Input Custom Value",
                                                  text=cur_val)
        if ok:
            self.model.setData(index, text.strip())
            return


class PropertiesDialog(BaseDialog):  # pragma: no cover
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
        self._title.setAlignment(Qt.AlignHCenter)
        self._form = QtWidgets.QFormLayout()

        self._btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        self._btns.accepted.connect(self.accept)

        vlayout.addWidget(self._title, alignment=Qt.AlignTop)
        vlayout.addLayout(self._form)
        vlayout.addWidget(self._btns, alignment=Qt.AlignBottom)

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
