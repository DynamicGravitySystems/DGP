# -*- coding: utf-8 -*-

"""
New pure data class for Meter configurations
"""
import configparser
import os
from typing import Optional

from ..oid import OID


class Gravimeter:
    def __init__(self, name: str, uid: Optional[str]=None, **kwargs):
        self._uid = OID(self, _uid=uid)
        self._type = "AT1A"
        self._name = name
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

    # TODO: Old methods from meterconfig - evaluate and reconfigure
    @staticmethod
    def get_valid_fields():
        # Sensor fields
        sensor_fields = ['g0', 'GravCal', 'LongCal', 'CrossCal', 'LongOffset', 'CrossOffset', 'stempgain',
                         'Temperature', 'stempoffset', 'pressgain', 'presszero', 'beamgain', 'beamzero',
                         'Etempgain', 'Etempzero']
        # Cross coupling Fields
        cc_fields = ['vcc', 've', 'al', 'ax', 'monitors']

        # Platform Fields
        platform_fields = ['Cross_Damping', 'Cross_Periode', 'Cross_Lead', 'Cross_Gain', 'Cross_Comp',
                           'Cross_Phcomp', 'Cross_sp', 'Long_Damping', 'Long_Periode', 'Long_Lead', 'Long_Gain',
                           'Long_Comp', 'Long_Phcomp', 'Long_sp', 'zerolong', 'zerocross', 'CrossSp', 'LongSp']

        # Create a set with all unique and valid field keys
        return set().union(sensor_fields, cc_fields, platform_fields)

    @staticmethod
    def process_config(valid_fields, **config):
        """Return a config dictionary by filtering out invalid fields, and lower-casing all keys"""
        def cast(value):
            try:
                return float(value)
            except ValueError:
                return value

        return {k.lower(): cast(v) for k, v in config.items() if k.lower() in map(str.lower, valid_fields)}

    @staticmethod
    def from_ini(path):
        """
        Read an AT1 Meter Configuration from a meter ini file
        :param path: path to meter ini file
        :return: instance of AT1Meter with configuration set by ini file
        """
        if not os.path.exists(path):
            raise OSError("Invalid path to ini.")
        config = configparser.ConfigParser(strict=False)
        config.read(path)

        sensor_fld = dict(config['Sensor'])
        xcoupling_fld = dict(config['crosscouplings'])
        platform_fld = dict(config['Platform'])

        name = str.strip(sensor_fld['meter'], '"')

        merge_config = {**sensor_fld, **xcoupling_fld, **platform_fld}
        # at1config = AT1Meter.process_config(AT1Meter.get_valid_fields(), **merge_config)
        # return AT1Meter(name, **at1config)


