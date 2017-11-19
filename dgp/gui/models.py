# coding: utf-8

"""
Provide definitions of the models used by the Qt Application in our
model/view widgets.
"""

import logging
from typing import List, Union

from PyQt5 import Qt, QtCore
from PyQt5.Qt import QWidget, QAbstractItemModel, QStandardItemModel
from PyQt5.QtCore import QModelIndex, QVariant
from PyQt5.QtGui import QIcon, QStandardItem
from PyQt5.QtWidgets import QComboBox

from dgp.gui.qtenum import QtDataRoles, QtItemFlags
from dgp.lib.types import AbstractTreeItem
# from dgp.lib.project import GravityProject


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

    def data(self, index: QModelIndex, role=None):
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            try:
                return self._rows[index.row()][index.column()]
            except IndexError:
                return None
        return QtCore.QVariant()

    def flags(self, index: QModelIndex):
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


class ProjectModel(QtCore.QAbstractItemModel):
    """Heirarchial (Tree) Project Model with a single root node."""
    def __init__(self, project: AbstractTreeItem, parent=None):
        super().__init__(parent=parent)
        # assert isinstance(project, GravityProject)
        project.model = self
        self._root_item = project
        self.log = logging.getLogger(__name__)
        self.layoutChanged.emit()
        self.log.info("Project Tree Model initialized.")

    def update(self, action=None, obj=None, **kwargs):
        """
        This simply emits layout change events to update the view.
        By calling layoutAboutToBeChanged and layoutChanged, we force an
        update of the entire layout that uses this model.
        This may not be as efficient as utilizing the beginInsertRows and
        endInsertRows signals to specify an exact range to update, but with
        the amount of data this model expects to handle, this is far less
        error prone and unnoticable.
        """
        self.layoutAboutToBeChanged.emit()
        self.log.info("ProjectModel Layout Changed")
        self.layoutChanged.emit()
        return
        # Deprecated in favor of calling simple layoutChanged signals
        if action.lower() == 'add':
            self.append_child(obj)
        elif action.lower() == 'del':
            parent = kwargs.get('parent', None)
            self.remove_child(parent, 0)

    def parent(self, index: QModelIndex) -> QModelIndex:
        """
        Returns the parent QModelIndex of the given index. If the object
        referenced by index does not have a parent (i.e. the root node) an
        invalid QModelIndex() is constructed and returned.
        e.g.

        Parameters
        ----------
        index: QModelIndex
            index to find parent of

        Returns
        -------
        QModelIndex:
            Valid QModelIndex of parent if exists, else
            Invalid QModelIndex() which references the root object
        """
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()  # type: AbstractTreeItem
        parent_item = child_item.parent  # type: AbstractTreeItem
        if parent_item == self._root_item:
            return QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    @staticmethod
    def data(index: QModelIndex,
             role: QtDataRoles) -> Union[QVariant, AbstractTreeItem]:
        """
        Returns data for the requested index and role.
        Parameters
        ----------
        index: QModelIndex
            Model Index of item to retrieve data from
        role: QtDataRoles
            Role from the enumerated Qt roles in dgp/gui/qtenum.py
            (Re-implemented for convenience and portability from PyQt defs)
        Returns
        -------
        Union[QVariant, AbstractTreeItem]:
            Returns QVariant data depending on specified role.
            If role is UserRole, the underlying AbstractTreeItem object is
            returned
        """
        if not index.isValid():
            return QVariant()

        item = index.internalPointer()  # type: AbstractTreeItem
        if role == QtDataRoles.UserRole:
            return item
        if role == QtDataRoles.DisplayRole:
            return item.data(QtDataRoles.DisplayRole)
            # return QVariant(str(item))
        else:
            data = item.data(role)
            # To guard against cases where certain roles not implemented
            if data is None:
                return QVariant()
            # print("209 Returning data ", data)
            return QVariant(data)

    @staticmethod
    def flags(index: QModelIndex) -> QtItemFlags:
        """Return the flags of an item at the specified ModelIndex"""
        if not index.isValid():
            return QtItemFlags.NoItemFlags
        # return index.internalPointer().flags()
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def headerData(self, section: int, orientation, role:
                   QtDataRoles=QtDataRoles.DisplayRole):
        """The Root item is responsible for first row header data"""
        if orientation == QtCore.Qt.Horizontal and role == QtDataRoles.DisplayRole:
            return self._root_item.data(role)
        return QVariant()

    @staticmethod
    def itemFromIndex(index: QModelIndex) -> AbstractTreeItem:
        """Returns the object referenced by index"""
        return index.internalPointer()

    # Experimental - doesn't work
    def index_from_item(self, item: AbstractTreeItem):
        """Iteratively walk through parents to generate an index"""
        parent = item.parent  # type: AbstractTreeItem
        chain = [item]
        while parent != self._root_item:
            print("Parent: ", parent.uid)
            chain.append(parent)
            parent = parent.parent
        print(chain)
        idx = {}
        for i, thing in enumerate(reversed(chain)):
            if i == 0:
                print("Index0: row", thing.row())
                idx[i] = self.index(thing.row(), 1, QModelIndex())
            else:
                idx[i] = self.index(thing.row(), 1, idx[i-1])
        print(idx)
        # print(idx[1].row())
        return idx[len(idx)-1]

    def index(self, row: int, column: int, parent: QModelIndex) -> QModelIndex:
        """Return a QModelIndex for the item at the given row and column,
        with the specified parent."""
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()  # type: AbstractTreeItem

        child_item = parent_item.child(row)
        # VITAL to compare is not None vs if child_item:
        if child_item is not None:
            return self.createIndex(row, column, child_item)
        else:
            return QModelIndex()

    def rowCount(self, parent: QModelIndex=QModelIndex(), *args, **kwargs):
        # *args and **kwargs are necessary to suppress Qt Warnings
        if parent.isValid():
            return parent.internalPointer().child_count()
        else:
            return self._root_item.child_count()

    @staticmethod
    def columnCount(parent: QModelIndex=QModelIndex(), *args, **kwargs):
        return 1


# QStyledItemDelegate
class SelectionDelegate(Qt.QStyledItemDelegate):
    def __init__(self, choices, parent=None):
        super().__init__(parent=parent)
        self._choices = choices

    def createEditor(self, parent: QWidget, option: Qt.QStyleOptionViewItem,
                     index: QModelIndex) -> QWidget:
        """Creates the editor widget to display in the view"""
        editor = QComboBox(parent)
        editor.setFrame(False)
        for choice in sorted(self._choices):
            editor.addItem(choice)
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        """Set the value displayed in the editor widget based on the model data
        at the index"""
        combobox = editor  # type: QComboBox
        value = str(index.model().data(index, QtDataRoles.EditRole))
        index = combobox.findText(value)  # returns -1 if value not found
        if index != -1:
            combobox.setCurrentIndex(index)
        else:
            combobox.addItem(value)
            combobox.setCurrentIndex(combobox.count() - 1)

    def setModelData(self, editor: QWidget, model: QAbstractItemModel,
                     index: QModelIndex) -> None:
        combobox = editor  # type: QComboBox
        value = str(combobox.currentText())
        row = index.row()
        for c in range(model.columnCount()):
            mindex = model.index(row, c)
            data = str(model.data(mindex, QtCore.Qt.DisplayRole))
            if data == value:
                model.setData(mindex, '<Unassigned>', QtCore.Qt.EditRole)
        model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor: QWidget, option: Qt.QStyleOptionViewItem,
                             index: QModelIndex) -> None:
        editor.setGeometry(option.rect)


# Experimental: Issue #36
class DataChannel(QStandardItem):
    def __init__(self):
        super().__init__(self)
        self.setDragEnabled(True)

    def onclick(self):
        pass


# Experimental: Drag-n-drop related to Issue #36
class ChannelListModel(QStandardItemModel):
    def __init__(self):
        pass

    def dropMimeData(self, QMimeData, Qt_DropAction, p, p1, QModelIndex):
        print("Mime data dropped")
        pass
