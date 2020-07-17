# -*- coding: utf-8 -*-

"""
New pure data class for Meter configurations
"""
import configparser
from pathlib import Path
from typing import Optional, Union, Dict

from dgp.core.types.reference import Reference
from dgp.core.oid import OID


sensor_fields = ['g0', 'GravCal', 'LongCal', 'CrossCal', 'LongOffset', 'CrossOffset', 'stempgain',
                 'Temperature', 'stempoffset', 'pressgain', 'presszero', 'beamgain', 'beamzero',
                 'Etempgain', 'Etempzero', 'Meter']
# Cross coupling Fields
cc_fields = ['vcc', 've', 'al', 'ax', 'monitors']

# Platform Fields
platform_fields = ['Cross_Damping', 'Cross_Periode', 'Cross_Lead', 'Cross_Gain', 'Cross_Comp',
                   'Cross_Phcomp', 'Cross_sp', 'Long_Damping', 'Long_Periode', 'Long_Lead', 'Long_Gain',
                   'Long_Comp', 'Long_Phcomp', 'Long_sp', 'zerolong', 'zerocross', 'CrossSp', 'LongSp']

valid_fields = set().union(sensor_fields, cc_fields, platform_fields)


class Gravimeter:
    def __init__(self, name: str, config: dict = None, uid: Optional[OID] = None, **kwargs):
        self._parent = Reference(self, 'parent')
        self.uid = uid or OID(self)
        self.uid.set_pointer(self)
        self.type = "AT1A"
        self.name = name
        self.column_format = "AT1A Airborne"
        self.config = config
        self.attributes = kwargs.get('attributes', {})

    @property
    def parent(self):
        return self._parent.dereference()

    @parent.setter
    def parent(self, value):
        self._parent.ref = value

    @staticmethod
    def read_config(path: Path) -> Dict[str, Union[str, int, float]]:
        if not path.exists():
            raise FileNotFoundError
        config = configparser.ConfigParser(strict=False)
        try:
            config.read(str(path))
        except configparser.MissingSectionHeaderError:
            return {}

        sensor_fld = dict(config['Sensor'])
        xcoupling_fld = dict(config['crosscouplings'])
        platform_fld = dict(config['Platform'])

        def safe_cast(value):
            try:
                return float(value)
            except ValueError:
                return value

        merged = {**sensor_fld, **xcoupling_fld, **platform_fld}
        return {k.lower(): safe_cast(v) for k, v in merged.items() if k.lower() in map(str.lower, valid_fields)}

    @classmethod
    def from_ini(cls, path: Path, name=None):
        """
        Read an AT1 Meter Configuration from a meter ini file
        """
        config = cls.read_config(Path(path))
        return cls(name, config=config)
