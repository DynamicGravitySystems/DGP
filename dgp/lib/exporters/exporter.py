# -*- coding: utf-8 -*-
from enum import Enum
from pathlib import Path
from typing import List


class TimeFormat(Enum):
    ISO8601 = '%Y-%m-%dT%H:%M:%S.%f%z'


class ExportProfile:
    __profiles = set()

    @classmethod
    def register(cls, profile):
        cls.__profiles.add(profile)

    @classmethod
    def profiles(cls):
        for profile in cls.__profiles:
            yield profile

    def __init__(self, name: str, columns: List[str] = None, ext: str = 'dat',
                 precision: int = 10, datum: str = "WGS84",
                 dateformat: TimeFormat = TimeFormat.ISO8601,
                 _userprofile: bool = True, register: bool = True):
        self.name = name
        self.columns = columns or []
        self.ext = ext
        self.precision = precision
        self.datum = datum
        self.dateformat = dateformat
        self._userprofile = _userprofile

        if register:
            ExportProfile.register(self)


class Exporter:
    __exporters = set()
    name = "Base Exporter"
    ext = 'dat'

    @classmethod
    def register(cls):
        """Explicitly register this class in the set of available exporters"""
        Exporter.__exporters.add(cls)

    @classmethod
    def exporters(cls):
        for exporter in Exporter.__exporters:
            yield exporter

    def __init__(self, name: str, *data, profile=None):
        self._name = name
        self._profile = profile

    @property
    def filename(self) -> str:
        return f'{self._name}.{self.ext}'

    @property
    def profile(self) -> ExportProfile:
        return self._profile

    @property
    def parameters(self):
        raise NotImplementedError

    def export(self, directory: Path):
        raise NotImplementedError
