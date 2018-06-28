# -*- coding: utf-8 -*-

"""
New pure data class for Meter configurations
"""
import configparser
import os
from typing import Optional

from dgp.core.oid import OID


sensor_fields = ['g0', 'GravCal', 'LongCal', 'CrossCal', 'LongOffset', 'CrossOffset', 'stempgain',
                 'Temperature', 'stempoffset', 'pressgain', 'presszero', 'beamgain', 'beamzero',
                 'Etempgain', 'Etempzero']
# Cross coupling Fields
cc_fields = ['vcc', 've', 'al', 'ax', 'monitors']

# Platform Fields
platform_fields = ['Cross_Damping', 'Cross_Periode', 'Cross_Lead', 'Cross_Gain', 'Cross_Comp',
                   'Cross_Phcomp', 'Cross_sp', 'Long_Damping', 'Long_Periode', 'Long_Lead', 'Long_Gain',
                   'Long_Comp', 'Long_Phcomp', 'Long_sp', 'zerolong', 'zerocross', 'CrossSp', 'LongSp']

valid_fields = set().union(sensor_fields, cc_fields, platform_fields)


class Gravimeter:
    def __init__(self, name: str, config: dict = None, uid: Optional[OID] = None, **kwargs):
        self._uid = uid or OID(self)
        self._uid.set_pointer(self)
        self._type = "AT1A"
        self._name = name
        self._column_format = "AT1A Airborne"
        self._config = config
        self._attributes = kwargs.get('attributes', {})

    @property
    def uid(self) -> OID:
        return self._uid

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        # ToDo: Regex validation?
        self._name = value

    @property
    def column_format(self):
        return self._column_format

    @property
    def sensor_type(self) -> str:
        return self._type

    @property
    def config(self) -> dict:
        return self._config

    @config.setter
    def config(self, value: dict) -> None:
        self._config = value

    @staticmethod
    def process_config(**config):
        """Return a config dictionary by filtering out invalid fields, and lower-casing all keys"""

        def safe_cast(value):
            try:
                return float(value)
            except ValueError:
                return value

        return {k.lower(): safe_cast(v) for k, v in config.items() if k.lower() in map(str.lower, valid_fields)}

    @classmethod
    def from_ini(cls, path, name=None):
        """
        Read an AT1 Meter Configuration from a meter ini file
        """
        if not os.path.exists(path):
            raise OSError("Invalid path to ini.")
        config = configparser.ConfigParser(strict=False)
        config.read(path)

        sensor_fld = dict(config['Sensor'])
        xcoupling_fld = dict(config['crosscouplings'])
        platform_fld = dict(config['Platform'])

        name = name or str.strip(sensor_fld['meter'], '"')

        merge_config = {**sensor_fld, **xcoupling_fld, **platform_fld}
        clean_config = cls.process_config(**merge_config)

        return cls(name, config=clean_config)

# TODO: Use sub-classes to define different Meter Types?

