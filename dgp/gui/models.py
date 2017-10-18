# coding: utf-8

"""Provide definitions of the models used by the Qt Application in our model/view widgets."""

from typing import List, Union

from PyQt5 import Qt, QtCore
from PyQt5.Qt import QWidget, QModelIndex, QAbstractItemModel
from PyQt5.QtCore import QModelIndex, QVariant
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QComboBox

from dgp.lib.types import TreeItem
from dgp.lib.project import Container, AirborneProject, Flight, MeterConfig


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


class ProjectItem:
    """
    ProjectItem is a wrapper for TreeItem descendants and/or simple string values, providing the necesarry interface to
    be utilized as an item in an AbstractModel (specifically ProjectModel, but theoretically any class derived from
    QAbstractItemModel).
    Items passed to this class are evaluated, if they are subclassed from TreeItem or an instance of ProjectItem their
    children (if any) will be wrapped (if not already) in a ProjectItem instance, and added as a child of this
    ProjectItem, allowing the creation of a nested tree type heirarchy.
    Due to the inspection of 'item's for children, this makes it effortless to create a tree from a single 'trunk', as
    the descendant (children) objects of a passed object that has children, will be automatically populated into the
    first ProjectItem's descendant list.
    If a supplied item does not have children, i.e. it is a string or other Python type, it will be stored internally,
    accessible via the 'object' property, and will be displayed to any QtView (e.g. QTreeView, QListView) as the
    string representation of the item, i.e. str(item), whatever that shall produce.
    """
    def __init__(self, item: Union['ProjectItem', TreeItem, str], parent: Union['ProjectItem', None]=None) -> None:
        """
        Initialize a ProjectItem for use in a Qt View.
        Parameters
        ----------
        item : Union[ProjectItem, TreeItem, str]
            An item to encapsulate for presentation within a Qt View (e.g. QTreeView)
            ProjectItem's and TreeItem's support the data(role) method, and as such the presentation of such objects can
            be more finely controlled in the implementation of the object itself.
            Other objects e.g. strings are simply displayed as is, or if an unsupported object is passed, the str() of
            the object is used as the display value.
        parent : Union[ProjectItem, None]
            The parent ProjectItem, (or None if this is the root object in a view) for this item.
        """
        self._parent = parent
        self._children = []
        self._object = item
        # _hasdata records whether the item is a class of ProjectItem or TreeItem, and thus has a data() method.
        self._hasdata = True

        if not issubclass(item.__class__, TreeItem) or isinstance(item, ProjectItem):
            self._hasdata = False
        if not hasattr(item, 'children'):
            return
        for child in item.children:
            self.append_child(child)

    @property
    def children(self):
        """Return generator for children of this ProjectItem"""
        for child in self._children:
            yield child

    @property
    def object(self) -> TreeItem:
        """Return the underlying class wrapped by this ProjectItem i.e. Flight"""
        return self._object

    def append_child(self, child) -> bool:
        """
        Appends a child object to this ProjectItem. If the passed child is already an instance of ProjectItem, the
        parent is updated to this object, and it is appended to the internal _children list.
        If the object is not an instance of ProjectItem, we attempt to encapsulated it, passing self as the parent, and
        append it to the _children list.
        Parameters
        ----------
        child

        Returns
        -------
        bool:
            True on success
        Raises
        ------
        TBD Exception on error
        """
        if not isinstance(child, ProjectItem):
            self._children.append(ProjectItem(child, self))
            return True
        child._parent = self
        self._children.append(child)
        return True

    def remove_child(self, child):
        """
        Attempts to remove a child object from the children of this ProjectItem
        Parameters
        ----------
        child: Union[TreeItem, str]
            The underlying object of a ProjectItem object. The ProjectItem that wraps 'child' will be determined by
            comparing the uid of the 'child' to the uid's of any object contained within the children of this
            ProjectItem.
        Returns
        -------
        bool:
            True on sucess
            False if the child cannot be located within the children of this ProjectItem.

        """
        for subitem in self._children[:]:  # type: ProjectItem
            if subitem.object.uid == child.uid:
                print("removing subitem: {}".format(subitem))
                self._children.remove(subitem)
                return True
        return False

    def child(self, row) -> Union['ProjectItem', None]:
        """Return the child ProjectItem at the given row, or None if the index does not exist."""
        try:
            return self._children[row]
        except IndexError:
            return None

    def indexof(self, child):
        if isinstance(child, ProjectItem):
            return self._children.index(child)
        for item in self._children:
            if item.object.uid == child.uid:
                return self._children.index(item)

    def child_count(self):
        return len(self._children)

    @staticmethod
    def column_count():
        return 1

    def data(self, role=None):
        # Allow the object to handle data display for certain roles
        if role in [QtCore.Qt.ToolTipRole, QtCore.Qt.DisplayRole, QtCore.Qt.UserRole]:
            if not self._hasdata:
                return str(self._object)
            return self._object.data(role)
        elif role == QtCore.Qt.DecorationRole:
            if not self._hasdata:
                return QVariant()
            icon = self._object.data(role)
            if icon is None:
                return QVariant()
            if not isinstance(icon, QIcon):
                # print("Creating QIcon")
                return QIcon(icon)
            return icon
        else:
            return QVariant()  # This is very important, otherwise the display gets screwed up.

    def row(self):
        """Reports this item's row location within parent's children list"""
        if self._parent:
            return self._parent.indexof(self)
        return 0

    def parent_item(self):
        return self._parent


# ProjectModel should eventually have methods to make changes to the underlying data structure, e.g.
# adding a flight, which would then update the model, without rebuilding the entire structure as
# is currently done.
# TODO: Can we inherit from AirborneProject, to create a single interface for modifying, and displaying the project?
class ProjectModel(QtCore.QAbstractItemModel):
    def __init__(self, project, parent=None):
        super().__init__(parent=parent)
        self._root_item = ProjectItem(project)
        self._project = project
        self._project.parent = self
        # Example of what the project structure/tree-view should look like
        # TODO: Will the structure contain actual objects (flights, meters etc) or str reprs
        # The ProjectItem data() method could retrieve a representation, and allow for powerful
        # data manipulations perhaps.
        # self.setup_model(project)

    def update(self, action, obj):
        if action.lower() == 'add':
            self.add_child(obj)
        elif action.lower() == 'remove':
            self.remove_child(obj)

    def add_child(self, item: Union[Flight, MeterConfig]):
        """
        Method to add a generic item of type Flight or MeterConfig to the project and model.
        In future add ability to add sub-children, e.g. FlightLines (although possibly in
        separate method).
        Parameters
        ----------
        item : Union[Flight, MeterConfig]
            Project Flights/Meters child object to add.

        Returns
        -------
        bool:
            True on successful addition
            False if the method could not add the item, i.e. could not match the container to
            insert the item.
        Raises
        ------
        NotImplementedError:
            Raised if item is not an instance of a recognized type, currently Flight or MeterConfig

        """
        for child in self._root_item.children:  # type: ProjectItem
            c_obj = child.object  # type: Container
            if isinstance(c_obj, Container) and issubclass(item.__class__, c_obj.ctype):
                # print("matched instance in add_child")
                cindex = self.createIndex(self._root_item.indexof(child), 1, child)
                self.beginInsertRows(cindex, len(c_obj), len(c_obj))
                c_obj.add_child(item)
                child.append_child(ProjectItem(item))
                self.endInsertRows()
                self.layoutChanged.emit()
                return True
        print("No match on contianer for object: {}".format(item))
        return False

    def remove_child(self, item):
        for wrapper in self._root_item.children:  # type: ProjectItem
            # Get the internal object representation (within the ProjectItem)
            c_obj = wrapper.object  # type: Container
            if isinstance(c_obj, Container) and c_obj.ctype == item.__class__:
                cindex = self.createIndex(self._root_item.indexof(wrapper), 1, wrapper)
                self.beginRemoveRows(cindex, wrapper.indexof(item), wrapper.indexof(item))
                c_obj.remove_child(item)
                # ProjectItem remove_child accepts a proper object (i.e. not a ProjectItem), and compares the UID
                wrapper.remove_child(item)
                self.endRemoveRows()
                return True
        return False

    def setup_model(self, base):
        for item in base.children:
            self._root_item.append_child(ProjectItem(item, self._root_item))

    def data(self, index: QModelIndex, role: int=None):
        if not index.isValid():
            return QVariant()

        item = index.internalPointer()  # type: ProjectItem
        if role == QtCore.Qt.UserRole:
            return item.object
        else:
            return item.data(role)

    def itemFromIndex(self, index: QModelIndex):
        return index.internalPointer()

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return 0
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def headerData(self, section: int, orientation, role: int=None):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._root_item.data(role)
        return QVariant()

    def index(self, row: int, column: int=0, parent: QModelIndex=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()  # type: ProjectItem
        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        else:
            return QModelIndex()

    def parent(self, index: QModelIndex):
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()  # type: ProjectItem
        parent_item = child_item.parent_item()  # type: ProjectItem
        if parent_item == self._root_item:
            return QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent: QModelIndex=QModelIndex(), *args, **kwargs):
        if parent.isValid():
            item = parent.internalPointer()  # type: ProjectItem
            return item.child_count()
        else:
            return self._root_item.child_count()

    def columnCount(self, parent: QModelIndex=QModelIndex(), *args, **kwargs):
        return 1

    # Highly Experimental:
    # Pass on attribute calls to the _project if this class has no such attribute
        # Unpickling encounters an error here (RecursionError)
    # def __getattr__(self, item):
    #     return getattr(self._project, item, None)

# QStyledItemDelegate
class SelectionDelegate(Qt.QStyledItemDelegate):
    def __init__(self, choices, parent=None):
        super().__init__(parent=parent)
        self._choices = choices

    def createEditor(self, parent: QWidget, option: Qt.QStyleOptionViewItem, index: QModelIndex) -> QWidget:
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

    def updateEditorGeometry(self, editor: QWidget, option: Qt.QStyleOptionViewItem, index: QModelIndex) -> None:
        editor.setGeometry(option.rect)



