# -*- coding: utf-8 -*-
from pathlib import Path

from pandas import DataFrame, concat

from .export_profile import ExportProfile

__all__ = ['Exporter']


class Exporter:
    __exporters = {}
    name = "Base Exporter"
    help = ""
    ext = 'dat'

    """Exporter Base Class
    
    This class cannot be instantiated directly.
    Sub-classes must implement the `export` method, and the `parameters` property
    
    Parameters
    ----------
    basename : str
        Base name for the file to be exported. Extension may be determined by
        the export profile.
    profile : :class:`ExportProfile`
    *data
    
    Attributes
    ----------
    name 
    help
    
    """

    @classmethod
    def register(cls):
        """Explicitly register this class in the set of available exporters"""
        Exporter.__exporters[cls.name] = cls

    @classmethod
    def exporters(cls):
        yield from Exporter.__exporters.values()

    def __init__(self, basename: str, profile: ExportProfile, *data):
        self._name = basename
        self._profile = profile
        self._data: DataFrame = concat(data, axis=1, sort=True)
        self._cols = [col for col in self._data]

    @property
    def columns(self):
        return [col for col in self.profile.columns if col in self._cols]

    @property
    def dataframe(self) -> DataFrame:
        if self.profile.precision:
            return self._data.round(decimals=self.profile.precision)
        else:
            return self._data

    @property
    def filename(self) -> str:
        if self.profile.ext:
            return f'{self._name}.{self.profile.ext}'
        else:
            return f'{self._name}.{self.ext}'

    @property
    def profile(self) -> ExportProfile:
        return self._profile

    @property
    def parameters(self):
        raise NotImplementedError

    def export(self, directory: Path):
        raise NotImplementedError
