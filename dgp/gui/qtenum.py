# coding: utf-8

"""This file redefines some common Qt Enumerations for easier use in code,
and to remove reliance on Qt imports in modules that do not directly
interact with Qt
See: http://pyqt.sourceforge.net/Docs/PyQt4/qt.html

The enum.IntFlag is not introduced until Python 3.6, but the enum.IntEnum
class is functionally equivalent for our purposes.
"""

import enum


class QtItemFlags(enum.IntEnum):
    """Qt Item Flags"""
    NoItemFlags = 0
    ItemIsSelectable = 1
    ItemIsEditable = 2
    ItemIsDragEnabled = 4
    ItemIsDropEnabled = 8
    ItemIsUserCheckable = 16
    ItemIsEnabled = 32
    ItemIsTristate = 64


class QtDataRoles(enum.IntEnum):
    """Qt Item Data Roles"""
    # Data to be rendered as text (QString)
    DisplayRole = 0
    # Data to be rendered as decoration (QColor, QIcon, QPixmap)
    DecorationRole = 1
    # Data displayed in edit mode (QString)
    EditRole = 2
    # Data to be displayed in a tooltip on hover (QString)
    ToolTipRole = 3
    # Data to be displayed in the status bar on hover (QString)
    StatusTipRole = 4
    WhatsThisRole = 5
    # Font used by the delegate to render this item (QFont)
    FontRole = 6
    TextAlignmentRole = 7
    # Background color used to render this item (QBrush)
    BackgroundRole = 8
    # Foreground or font color used to render this item (QBrush)
    ForegroundRole = 9
    CheckStateRole = 10
    SizeHintRole = 13
    InitialSortOrderRole = 14

    UserRole = 32
    UIDRole = 33
