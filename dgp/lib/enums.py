# coding: utf-8

import enum
import logging

"""
Dynamic Gravity Processor (DGP) :: lib/enums.py
License: Apache License V2

Overview:
enums.py consolidates various enumeration structures used throughout the project

Compatibility:
As we are still currently targetting Python 3.5 the following Enum classes 
cannot be used - they are not introduced until Python 3.6

- enum.Flag
- enum.IntFlag
- enum.auto

"""


LOG_LEVEL_MAP = {'debug': logging.DEBUG, 'info': logging.INFO,
                 'warning': logging.WARNING, 'error': logging.ERROR,
                 'critical': logging.CRITICAL}


class LogColors(enum.Enum):
    DEBUG = 'blue'
    INFO = 'yellow'
    WARNING = 'brown'
    ERROR = 'red'
    CRITICAL = 'orange'


class ProjectTypes(enum.Enum):
    AIRBORNE = 'airborne'
    MARINE = 'marine'


class MeterTypes(enum.Enum):
    """Gravity Meter Types"""
    AT1A = 'at1a'
    AT1M = 'at1m'
    ZLS = 'zls'
    TAGS = 'tags'


class DataTypes(enum.Enum):
    """Gravity/Trajectory Data Types"""
    # TODO: Add different GPS format enums
    GRAVITY = 'gravity'
    TRAJECTORY = 'trajectory'
    AT1A = 'at1a'
    AT1M = 'at1m'
    ZLS = 'zls'
    TAGS = 'tags'


class GPSFields(enum.Enum):
    sow = {'week', 'sow', 'lat', 'long', 'ell_ht'}
    hms = {'mdy', 'hms', 'lat', 'long', 'ell_ht'}
    serial = {'datenum', 'lat', 'long', 'ell_ht'}


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

