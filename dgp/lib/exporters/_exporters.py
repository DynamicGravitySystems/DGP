# -*- coding: utf-8 -*-
from pathlib import Path

from .exporter import Exporter


__all__ = ['CSVExporter', 'JSONExporter', 'HDFExporter']


class CSVExporter(Exporter):
    name = "CSV Exporter"
    help = "Export data to a CSV (comma-separated value) formatted file"

    @property
    def parameters(self):
        return {
            'header': bool,
            'index_label': str
        }

    def export(self, directory: Path):
        file = directory.joinpath(self.filename)
        with file.open('w') as fd:
            self.dataframe.to_csv(fd, columns=self.columns, header=True,
                                  index_label='datetime',
                                  date_format=self.profile.dateformat.value)


class JSONExporter(Exporter):
    name = "JSON Exporter"
    help = "Export data to a Java Standard Object Notation (JSON) formatted file"

    @property
    def parameters(self):
        return {}

    def export(self, directory: Path):
        file = directory.joinpath(self.filename)
        with file.open('w') as fd:
            self.dataframe.to_json(fd, orient='columns', date_format='iso')


class HDFExporter(Exporter):
    name = "HDF5 Exporter"

    @property
    def parameters(self):
        return {}

    def export(self, directory: Path):
        return


JSONExporter.register()
CSVExporter.register()
HDFExporter.register()
