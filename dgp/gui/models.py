# coding: utf-8

import logging
from typing import List, Dict

import PyQt5.QtCore as QtCore
import PyQt5.Qt as Qt
from PyQt5.Qt import QWidget
from PyQt5.QtCore import (QModelIndex, QVariant, QAbstractItemModel,
                          QMimeData, pyqtSignal, pyqtBoundSignal)
from PyQt5.QtGui import QIcon, QBrush, QColor
from PyQt5.QtWidgets import QComboBox

from dgp.gui.qtenum import QtDataRoles, QtItemFlags
from dgp.lib.types import (AbstractTreeItem, BaseTreeItem, TreeItem,
                           ChannelListHeader, DataChannel)
from dgp.lib.etc import gen_uuid

"""
Dynamic Gravity Processor (DGP) :: gui/models.py
License: Apache License V2

Overview:
Defines the various custom Qt Models derived from QAbstract*Model used to 
display data in the graphical interface via a Q*View (List/Tree/Table)

See Also
--------
dgp.lib.types.py : Defines many of the objects used within the models

"""


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
        """Populates the model with key, value pairs from the passed objects'
        __dict__"""
        for key, value in obj.__dict__.items():
            self.append(key, value)

    def append(self, *args):
        """Add a new row of data to the table, trimming input array to length of
         columns."""
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
                return QtCore.QVariant()
        return QtCore.QVariant()

    def flags(self, index: QModelIndex):
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        if index.row() == 0 and self._editheader:
            flags = flags | QtCore.Qt.ItemIsEditable
        # Allow the values column to be edited
        elif self._editable is not None and index.column() in self._editable:
            flags = flags | QtCore.Qt.ItemIsEditable
        return flags

    def headerData(self, section, orientation, role=None):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return QVariant(section)
            # return self._cols[section]

    # Required implementations of super class for editable table

    def setData(self, index: QtCore.QModelIndex, value: QtCore.QVariant, role=None):
        """Basic implementation of editable model. This doesn't propagate the
        changes to the underlying object upon which the model was based
        though (yet)"""
        if index.isValid() and role == QtCore.Qt.ItemIsEditable:
            self._rows[index.row()][index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        else:
            return False


class TableModel2(QtCore.QAbstractTableModel):
    """Simple table model of key: value pairs.
    Parameters
    ----------
    data : List
    2D List of data by rows/columns, data[0] is assumed to contain the column
    headers for the data.
    """

    def __init__(self, data, parent=None):
        super().__init__(parent=parent)

        self._data = data

    def header_row(self):
        return self._data[0]

    def value_at(self, row, col):
        return self._data[row][col]

    def set_row(self, index, values):
        try:
            nvals = list(values)
            while len(nvals) < self.columnCount():
                nvals.append(' ')
            self._data[index] = nvals
        except IndexError:
            print("Unable to set data at index: ", index)
            return False
        self.dataChanged.emit(self.index(index, 0),
                              self.index(index, len(self._data[index])))
        return True

    # Required implementations of super class (for a basic, non-editable table)

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self._data)

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self._data[0])

    def data(self, index: QModelIndex, role=None):
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            try:
                val = self._data[index.row()][index.column()]
                return val
            except IndexError:
                return QtCore.QVariant()
        return QtCore.QVariant()

    def flags(self, index: QModelIndex):
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        if index.row() == 0:
            # Allow editing of first row (Column headers)
            flags = flags | QtCore.Qt.ItemIsEditable
        return flags

    def headerData(self, section, orientation, role=None):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return QtCore.QVariant()

    # Required implementations of super class for editable table

    def setData(self, index: QtCore.QModelIndex, value, role=None):
        """Basic implementation of editable model. This doesn't propagate the
        changes to the underlying object upon which the model was based
        though (yet)"""
        if index.isValid() and role == QtCore.Qt.ItemIsEditable:
            self._data[index.row()][index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        else:
            return False


class BaseTreeModel(QAbstractItemModel):
    """
    Define common methods required for a Tree Model based on
    QAbstractItemModel.
    Subclasses must provide implementations for update() and data()
    """
    def __init__(self, root_item: AbstractTreeItem, parent=None):
        super().__init__(parent=parent)
        self._root = root_item

    @property
    def root(self):
        return self._root

    def parent(self, index: QModelIndex=QModelIndex()) -> QModelIndex:
        """
        Returns the parent QModelIndex of the given index. If the object
        referenced by index does not have a parent (i.e. the root node) an
        invalid QModelIndex() is constructed and returned.
        """
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()  # type: AbstractTreeItem
        parent_item = child_item.parent  # type: AbstractTreeItem
        if parent_item == self._root or parent_item is None:
            return QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def update(self, *args, **kwargs):
        raise NotImplementedError("Update must be implemented by subclass.")

    def data(self, index: QModelIndex, role: QtDataRoles=None):
        raise NotImplementedError("data() must be implemented by subclass.")

    def flags(self, index: QModelIndex) -> QtItemFlags:
        """Return the flags of an item at the specified ModelIndex"""
        if not index.isValid():
            return QtItemFlags.NoItemFlags
        return index.internalPointer().flags()

    @staticmethod
    def itemFromIndex(index: QModelIndex) -> AbstractTreeItem:
        """Returns the object referenced by index"""
        return index.internalPointer()

    @staticmethod
    def columnCount(parent: QModelIndex=QModelIndex(), *args, **kwargs):
        return 1

    def headerData(self, section: int, orientation, role:
                   QtDataRoles=QtDataRoles.DisplayRole):
        """The Root item is responsible for first row header data"""
        if orientation == QtCore.Qt.Horizontal and role == QtDataRoles.DisplayRole:
            return self._root.data(role)
        return QVariant()

    def index(self, row: int, col: int, parent: QModelIndex=QModelIndex(),
              *args, **kwargs) -> QModelIndex:
        """Return a QModelIndex for the item at the given row and column,
        with the specified parent."""
        if not self.hasIndex(row, col, parent):
            return QModelIndex()
        if not parent.isValid():
            parent_item = self._root
        else:
            parent_item = parent.internalPointer()  # type: AbstractTreeItem

        child_item = parent_item.child(row)
        # VITAL to compare is not None vs if child_item:
        if child_item is not None:
            return self.createIndex(row, col, child_item)
        else:
            return QModelIndex()

    def rowCount(self, parent: QModelIndex=QModelIndex(), *args, **kwargs):
        # *args and **kwargs are necessary to suppress Qt Warnings
        if parent.isValid():
            return parent.internalPointer().child_count()
        return self._root.child_count()


class ProjectModel(BaseTreeModel):
    """Heirarchial (Tree) Project Model with a single root node."""
    def __init__(self, project: AbstractTreeItem, parent=None):
        self.log = logging.getLogger(__name__)
        super().__init__(TreeItem("root"), parent=parent)
        # assert isinstance(project, GravityProject)
        project.model = self
        self.root.append_child(project)
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

    def data(self, index: QModelIndex, role: QtDataRoles=None):
        """
        Returns data for the requested index and role.
        We do some processing here to encapsulate data within Qt Types where
        necesarry, as TreeItems in general do not import Qt Modules due to
        the possibilty of pickling them.
        Parameters
        ----------
        index: QModelIndex
            Model Index of item to retrieve data from
        role: QtDataRoles
            Role from the enumerated Qt roles in dgp/gui/qtenum.py
            (Re-implemented for convenience and portability from PyQt defs)
        Returns
        -------
        QVariant
            Returns QVariant data depending on specified role.
            If role is UserRole, the underlying AbstractTreeItem object is
            returned
        """
        if not index.isValid():
            return QVariant()
        item = index.internalPointer()  # type: AbstractTreeItem
        data = item.data(role)

        # To guard against cases where role is not implemented
        if data is None:
            return QVariant()

        # Role encapsulation
        if role == QtDataRoles.UserRole:
            return item
        if role == QtDataRoles.DecorationRole:
            # Construct Decoration object from data
            return QIcon(data)
        if role in [QtDataRoles.BackgroundRole, QtDataRoles.ForegroundRole]:
            return QBrush(QColor(data))

        return QVariant(data)

    def flags(self, index: QModelIndex) -> QtItemFlags:
        """Return the flags of an item at the specified ModelIndex"""
        if not index.isValid():
            return QtItemFlags.NoItemFlags
        # return index.internalPointer().flags()
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled


class ComboEditDelegate(Qt.QStyledItemDelegate):
    """Used by the Advanced Import Dialog to enable column selection/setting."""
    def __init__(self, options=None, parent=None):
        super().__init__(parent=parent)
        self._options = options

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, value):
        self._options = list(value)

    def createEditor(self, parent: QWidget, option: Qt.QStyleOptionViewItem,
                     index: QModelIndex) -> QWidget:
        """
        Create the Editor widget. The widget will be populated with data in
        the setEditorData method, which is called by the view immediately
        after creation of the editor.

        Parameters
        ----------
        parent
        option
        index

        Returns
        -------
        QWidget

        """
        editor = QComboBox(parent)
        editor.setFrame(False)
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        """
        Sets the options in the supplied editor widget. This delegate class
        expects a QComboBox widget, and will populate the combobox with
        options supplied by the self.options property, or will construct them
        from the current row if self.options is None.

        Parameters
        ----------
        editor
        index

        Returns
        -------

        """
        if not isinstance(editor, QComboBox):
            print("Unexpected editor type.")
            return
        value = str(index.model().data(index, QtDataRoles.EditRole))
        if self.options is None:
            # Construct set of choices by scanning columns at the current row
            model = index.model()
            row = index.row()
            self.options = {model.data(model.index(row, c), QtDataRoles.EditRole)
                            for c in range(model.columnCount())}

        for choice in sorted(self.options):
            editor.addItem(choice)

        index = editor.findText(value, flags=Qt.Qt.MatchExactly)
        if editor.currentIndex() == index:
            return
        elif index == -1:
            # -1 is returned by findText if text is not found
            # In this case add the value to list of options in combobox
            editor.addItem(value)
            editor.setCurrentIndex(editor.count() - 1)
        else:
            editor.setCurrentIndex(index)

    def setModelData(self, editor: QWidget, model: QAbstractItemModel,
                     index: QModelIndex) -> None:
        combobox = editor  # type: QComboBox
        value = str(combobox.currentText())
        model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor: QWidget,
                             option: Qt.QStyleOptionViewItem,
                             index: QModelIndex) -> None:
        editor.setGeometry(option.rect)


class ChannelListModel(BaseTreeModel):
    """
    Tree type model for displaying/plotting data channels.
    This model supports drag and drop internally.

    Attributes
    ----------
    _plots : dict(int, ChannelListHeader)
        Mapping of plot index to the associated Tree Item of type
        ChannelListHeader
    channels : dict(str, DataChannel)
        Mapping of DataChannel UID to DataChannel
    _default : ChannelListHeader
        The default container for channels if they are not assigned to a plot
    plotOverflow : pyqtSignal(str)
        Signal emitted when drop operation would result in too many children,
        ChannelListHeader.uid is passed.
    channelChanged : pyqtSignal(int, DataChannel)
        Signal emitted when DataChannel has been dropped to new parent/header
        Emits index of new header, and the DataChannel that was changed.

    """

    plotOverflow = pyqtSignal(str)  # type: pyqtBoundSignal
    channelChanged = pyqtSignal(int, DataChannel)  # type: pyqtBoundSignal

    def __init__(self, channels: List[DataChannel], plots: int, parent=None):
        super().__init__(BaseTreeItem(gen_uuid('base')), parent=parent)
        self._plots = {}
        for i in range(plots):
            plt_header = ChannelListHeader(i, ctype='Plot', max_children=2)
            self._plots[i] = plt_header
            self.root.append_child(plt_header)

        self._default = ChannelListHeader()
        self.root.append_child(self._default)

        self.channels = self._build_model(channels)

    def _build_model(self, channels: list) -> Dict[str, DataChannel]:
        """Build the model representation"""
        rv = {}
        for dc in channels:  # type: DataChannel
            rv[dc.uid] = dc
            if dc.index == -1:
                self._default.append_child(dc)
                continue
            try:
                self._plots[dc.index].append_child(dc)
            except KeyError:
                self.log.warning('Channel {} could not be plotted, plot does '
                                 'not exist'.format(dc.uid))
                dc.plot(None)
                self._default.append_child(dc)
        return rv

    def clear(self):
        """Remove all channels from the model"""
        for dc in self.channels.values():
            dc.orphan()
        self.channels = None
        self.update()

    def set_channels(self, channels: list):
        self.clear()
        self.channels = self._build_model(channels)
        self.update()

    def move_channel(self, uid, index) -> bool:
        """Move channel specified by uid to parent at index"""
        raise NotImplementedError("Method not yet implemented or required.")

    def update(self) -> None:
        """Update the models view layout."""
        self.layoutAboutToBeChanged.emit()
        self.layoutChanged.emit()

    def data(self, index: QModelIndex, role: QtDataRoles=None):
        item_data = index.internalPointer().data(role)
        if item_data is None:
            return QVariant()
        return item_data

    def flags(self, index: QModelIndex):
        item = index.internalPointer()
        if item == self.root:
            return QtCore.Qt.NoItemFlags
        if isinstance(item, DataChannel):
            return (QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable |
                    QtCore.Qt.ItemIsEnabled)
        return (QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsDropEnabled)

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def supportedDragActions(self):
        return QtCore.Qt.MoveAction

    def dropMimeData(self, data: QMimeData, action, row, col,
                     parent: QModelIndex) -> bool:
        """
        Called by the Q*x*View when a Mime Data object is dropped within its
        frame.
        This model supports only the Qt.MoveAction, and will reject any others.
        This method will check several properties before accepting/executing
        the drop action.

          - Verify that action == Qt.MoveAction
          - Ensure data.hasText() is True
          - Lookup the channel referenced by data, ensure it exists
          - Check that the destination (parent) will not exceed its max_child
            limit if the drop is accepted.

        Also note that if a channel is somehow dropped to an invalid index,
        it will simply be added back to the default container (Available
        Channels)

        Parameters
        ----------
        data : QMimeData
            A QMimeData object containing text data with a DataChannel UID
        action : Qt.DropActions
            An Enum/Flag passed by the View. Must be of value Qt::MoveAction
        row, col : int
            Row and column of the parent that the data has been dropped on/in.
            If row and col are both -1, the data has been dropped directly on
            the parent.
        parent : QModelIndex
            The QModelIndex of the model item that the data has been dropped
            in or on.

        Returns
        -------
        result : bool
            True on sucessful drop.
            False if drop is rejected.
            Failure may be due to the parent having too many children,
            or the data did not have a properly encoded UID string, or the
            UID could not be looked up in the model channels.

        """
        if action != QtCore.Qt.MoveAction:
            return False
        if not data.hasText():
            return False

        dc = self.channels.get(data.text(), None)  # type: DataChannel
        if dc is None:
            return False

        if not parent.isValid():
            # An invalid parent can be caused if an item is dropped between
            # headers, as its parent is then the root object. In this case
            # try to get the header it was dropped under from the _plots map.
            # If we can get a valid ChannelListHeader, set destination to
            # that, and recreate the parent QModelIndex to point refer to the
            # new destination.
            if row-1 in self._plots:
                destination = self._plots[row-1]
                parent = self.index(row-1, 0)
            else:
                # Otherwise if the object was in the _default header, and is
                # dropped in an invalid manner, don't remove and re-add it to
                # the _default, just abort the move.
                if dc.parent == self._default:
                    return False
                destination = self._default
                parent = self.index(self._default.row(), 0)
        else:
            destination = parent.internalPointer()

        if destination.max_children is not None and (
                destination.child_count() + 1 > destination.max_children):
            self.plotOverflow.emit(destination.uid)
            return False

        old_index = self.index(dc.parent.row(), 0)
        # Remove channel from old parent/header
        self.beginRemoveRows(old_index, dc.row(), dc.row())
        dc.orphan()
        self.endRemoveRows()

        # Add channel to new parent/header
        n_row = destination.child_count()
        self.beginInsertRows(parent, n_row, n_row)
        destination.append_child(dc)
        self.endInsertRows()

        self.channelChanged.emit(destination.index, dc)
        self.update()
        return True

    def canDropMimeData(self, data: QMimeData, action, row, col, parent:
                        QModelIndex) -> bool:
        """
        Queried when Mime data is dragged over/into the model. Returns 
        True if the data can be dropped. Does not guarantee that it will be 
        accepted.
        
        This method simply checks that the data has text within it.
        
        Returns
        -------
        canDrop : bool
            True if data can be dropped at the hover location.
            False if the data cannot be dropped at the location.
        """
        if data.hasText():
            return True
        return False

    def mimeData(self, indexes) -> QMimeData:
        """
        Create a QMimeData object for the item(s) specified by indexes.

        This model simply encodes the UID of the selected item (index 0 of
        indexes - single selection only), into text/plain MIME object.

        Parameters
        ----------
        indexes : list(QModelIndex)
            List of QModelIndexes of the selected model items.

        Returns
        -------
        QMimeData
            text/plain QMimeData object, containing model item UID.

        """
        index = indexes[0]
        item_uid = index.internalPointer().uid
        data = QMimeData()
        data.setText(item_uid)
        return data
