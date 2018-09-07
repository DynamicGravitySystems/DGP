# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict

from pandas import MultiIndex, DataFrame

from .exporter import Exporter

__all__ = ['CSVExporter', 'JSONExporter', 'HDFExporter']


class CSVExporter(Exporter):
    name = "CSV Exporter"
    help = "Export data to a CSV (comma-separated value) formatted file"
    ext = 'csv'

    @property
    def parameters(self):
        return {
            'header': bool,
            'index_label': str
        }

    def export(self, descriptor):
        data = self.data
        cols = [col for col in data if col in self.profile.columns]

        data.to_csv(descriptor, columns=cols, header=True, index=True,
                    date_format=self.profile.dateformat.value)


class JSONExporter(Exporter):
    name = "JSON Exporter"
    help = "Export data to a Java Standard Object Notation (JSON) formatted file"
    ext = 'json'

    @property
    def parameters(self):
        return {}

    def export(self, descriptor):
        self.data.to_json(descriptor, orient='columns', date_format='iso')


class HDFExporter(Exporter):
    name = "HDF5 Exporter"
    ext = 'hdf5'

    @property
    def parameters(self):
        return {}

    def export(self, directory: Path):
        return


JSONExporter.register()
CSVExporter.register()
HDFExporter.register()
