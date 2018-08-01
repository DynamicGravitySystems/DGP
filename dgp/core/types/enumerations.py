# -*- coding: utf-8 -*-

import enum
import logging

"""
Dynamic Gravity Processor (DGP) :: lib/enumerations.py
License: Apache License V2

Overview:
enumerations.py consolidates various enumeration structures used throughout the project

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


class StateColor(enum.Enum):
    ACTIVE = '#11dd11'
    INACTIVE = '#ffffff'


class Icon(enum.Enum):
    """Resource Icon paths for Qt resources"""
    OPEN_FOLDER = ":/icons/folder_open.jpg"
    AIRBORNE = ":/icons/airborne"
    MARINE = ":/icons/marine"
    METER = ":/icons/meter_config.png"
    DGS = ":/icons/dgs"
    GRAVITY = ":/icons/gravity"
    TRAJECTORY = ":/icons/gps"
    NEW_FILE = ":/icons/new_file.png"
    SAVE = ":/icons/save_project.png"
    ARROW_LEFT = ":/icons/chevron-right"
    ARROW_DOWN = ":/icons/chevron-down"


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
    GRAVITY = 'gravity'
    TRAJECTORY = 'trajectory'


class GravityTypes(enum.Enum):
    # TODO: add set of fields specific to each dtype
    AT1A = ('gravity', 'long_accel', 'cross_accel', 'beam', 'temp', 'status',
            'pressure', 'Etemp', 'gps_week', 'gps_sow')
    AT1M = ('at1m',)
    ZLS = ('line_name', 'year', 'day', 'hour', 'minute', 'second', 'sensor',
           'spring_tension', 'cross_coupling', 'raw_beam', 'vcc', 'al', 'ax',
           've2', 'ax2', 'xacc2', 'lacc2', 'xacc', 'lacc', 'par_port',
           'platform_period')
    TAGS = ('tags', )


# TODO: I don't like encoding the field tuples in enum - do a separate lookup?
class GPSFields(enum.Enum):
    sow = ('week', 'sow', 'lat', 'long', 'ell_ht')
    hms = ('mdy', 'hms', 'lat', 'long', 'ell_ht')
    serial = ('datenum', 'lat', 'long', 'ell_ht')


