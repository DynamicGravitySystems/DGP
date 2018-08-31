# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Union

from pandas import DataFrame, Series, concat
from .exporter import Exporter


class CSVExporter(Exporter):
    name = "CSV Exporter"
    ext = 'csv'

    def __init__(self, name: str, *data: Union[DataFrame, Series], profile=None):
        super().__init__(name=name, profile=profile)
        self._data: DataFrame = concat(data, axis=1, sort=True)

    @property
    def parameters(self):
        return {
            'header': bool,
            'index_label': str
        }

    def export(self, directory: Path):
        file = directory.joinpath(self.filename)

        rounded = self._data.round(decimals=self.profile.precision)
        cols = [col for col in self.profile.columns if col in self._data]

        with file.open('w') as fd:
            rounded.to_csv(fd, columns=cols, header=True,
                           index_label='datetime',
                           date_format=self.profile.dateformat.value)


CSVExporter.register()
