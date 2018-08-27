# -*- coding: utf-8 -*-
import logging
from enum import Enum, auto

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QIcon

__all__ = ['StateAction', 'StateColor', 'Icon', 'ProjectTypes',
           'MeterTypes', 'DataType']

LOG_LEVEL_MAP = {'debug': logging.DEBUG, 'info': logging.INFO,
                 'warning': logging.WARNING, 'error': logging.ERROR,
                 'critical': logging.CRITICAL}


class StateAction(Enum):
    CREATE = auto()
    UPDATE = auto()
    DELETE = auto()


class StateColor(Enum):
    ACTIVE = '#11dd11'
    INACTIVE = '#ffffff'


class Icon(Enum):
    """Resource Icon paths for Qt resources"""
    AUTOSIZE = "autosize"
    OPEN_FOLDER = "folder_open"
    AIRBORNE = "airborne"
    MARINE = "marine"
    METER = "sensor"
    DGS = "dgs"
    DGP = "dgp_large"
    DGP_SMALL = "dgp"
    DGP_NOTEXT = "dgp_notext"
    GRAVITY = "gravity"
    TRAJECTORY = "gps"
    NEW_FILE = "new_file"
    SAVE = "save"
    DELETE = "delete"
    ARROW_LEFT = "chevron-left"
    ARROW_RIGHT = "chevron-right"
    ARROW_UP = "chevron-up"
    ARROW_DOWN = "chevron-down"
    LINE_MODE = "line_mode"
    PLOT_LINE = "plot_line"
    SETTINGS = "settings"
    SELECT = "select"
    INFO = "info"
    HELP = "help_outline"
    GRID = "grid_on"
    NO_GRID = "grid_off"
    TREE = "tree"

    def icon(self, prefix="icons"):
        return QIcon(f':/{prefix}/{self.value}')


class LogColors(Enum):
    DEBUG = 'blue'
    INFO = 'yellow'
    WARNING = 'brown'
    ERROR = 'red'
    CRITICAL = 'orange'


class ProjectTypes(Enum):
    AIRBORNE = 'airborne'
    MARINE = 'marine'


class MeterTypes(Enum):
    """Gravity Meter Types"""
    AT1A = 'at1a'
    AT1M = 'at1m'
    ZLS = 'zls'
    TAGS = 'tags'


class DataType(Enum):
    """Gravity/Trajectory Data Types"""
    GRAVITY = 'gravity'
    TRAJECTORY = 'trajectory'


class GravityTypes(Enum):
    # TODO: add set of fields specific to each dtype
    AT1A = ('gravity', 'long_accel', 'cross_accel', 'beam', 'temp', 'status',
            'pressure', 'Etemp', 'gps_week', 'gps_sow')
    AT1M = ('at1m',)
    ZLS = ('line_name', 'year', 'day', 'hour', 'minute', 'second', 'sensor',
           'spring_tension', 'cross_coupling', 'raw_beam', 'vcc', 'al', 'ax',
           've2', 'ax2', 'xacc2', 'lacc2', 'xacc', 'lacc', 'par_port',
           'platform_period')
    TAGS = ('tags', )


class GPSFields(Enum):
    sow = ('week', 'sow', 'lat', 'long', 'ell_ht')
    hms = ('mdy', 'hms', 'lat', 'long', 'ell_ht')
    serial = ('datenum', 'lat', 'long', 'ell_ht')


class Links(Enum):
    DEV_DOCS = "https://dgp.readthedocs.io/en/develop/"
    MASTER_DOCS = "https://dgp.readthedocs.io/en/latest/"
    GITHUB = "https://github.com/DynamicGravitySystems/DGP"

    def url(self):
        return QUrl(self.value)
