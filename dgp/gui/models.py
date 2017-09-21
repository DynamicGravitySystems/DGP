# coding: utf-8

"""Provide definitions of the models used by the Qt Application in our model/view widgets."""

from PyQt5 import QtCore, QtWidgets, Qt
from PyQt5.Qt import QWidget, QModelIndex, QAbstractItemModel, QStyleOptionViewItem, QComboBox


class TableModel(QtCore.QAbstractTableModel):
    """Simple table model of key: value pairs."""

    def __init__(self, columns, editable=None, editheader=False, parent=None):
        super().__init__(parent=parent)
        # TODO: Allow specification of which columns are editable
        # List of column headers
        self._cols = columns
        self._rows = []
        self._editable = editable
        self._editheader = editheader
        self._updates = {}

    def set_object(self, obj):
        """Populates the model with key, value pairs from the passed objects' __dict__"""
        for key, value in obj.__dict__.items():
            self.append(key, value)

    def append(self, *args):
        """Add a new row of data to the table, trimming input array to length of columns."""
        if not isinstance(args, list):
            args = list(args)
        while len(args) < len(self._cols):
            # Pad the end
            args.append(None)

        self._rows.append(args[:len(self._cols)])
        return True

    def get_row(self, row: int):
        try:
            return self._rows[row]
        except IndexError:
            print("Invalid row index")
            return None

    @property
    def updates(self):
        return self._updates

    @property
    def data(self):
        # TODO: Work on some sort of mapping to map column headers to row values
        return self._rows

    # Required implementations of super class (for a basic, non-editable table)

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self._rows)

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self._cols)

    def data(self, index: QtCore.QModelIndex, role=None):
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            try:
                return self._rows[index.row()][index.column()]
            except IndexError:
                return None
        return QtCore.QVariant()

    def flags(self, index: QtCore.QModelIndex):
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        if index.row() == 0 and self._editheader:
            flags = flags | QtCore.Qt.ItemIsEditable
        elif self._editable is not None and index.column() in self._editable:  # Allow the values column to be edited
            flags = flags | QtCore.Qt.ItemIsEditable
        return flags

    def headerData(self, section, orientation, role=None):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self._cols[section]

    # Required implementations of super class for editable table

    def setData(self, index: QtCore.QModelIndex, value: QtCore.QVariant, role=None):
        """Basic implementation of editable model. This doesn't propagate the changes to the underlying
        object upon which the model was based though (yet)"""
        if index.isValid() and role == QtCore.Qt.ItemIsEditable:
            self._rows[index.row()][index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        else:
            return False


class SelectionDelegate(Qt.QStyledItemDelegate):
    def __init__(self, choices, parent=None):
        super().__init__(parent=parent)
        self._choices = choices

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        """Creates the editor widget to display in the view"""
        editor = QComboBox(parent)
        editor.setFrame(False)
        for choice in sorted(self._choices):
            editor.addItem(choice)
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        """Set the value displayed in the editor widget based on the model data at the index"""
        combobox = editor  # type: QComboBox
        value = str(index.model().data(index, QtCore.Qt.EditRole))
        index = combobox.findText(value)  # returns -1 if value not found
        if index != -1:
            combobox.setCurrentIndex(index)
        else:
            combobox.addItem(value)
            combobox.setCurrentIndex(combobox.count() - 1)

    def setModelData(self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex) -> None:
        combobox = editor  # type: QComboBox
        value = str(combobox.currentText())
        row = index.row()
        for c in range(model.columnCount()):
            mindex = model.index(row, c)
            data = str(model.data(mindex, QtCore.Qt.DisplayRole))
            if data == value:
                model.setData(mindex, '<Unassigned>', QtCore.Qt.EditRole)
        model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        editor.setGeometry(option.rect)



