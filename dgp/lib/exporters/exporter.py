# -*- coding: utf-8 -*-
from pandas import DataFrame

from .export_profile import ExportProfile

__all__ = ['Exportable', 'Exporter']


class Exportable:
    def export(self, recursive=True) -> DataFrame:
        """Return a multi-indexed DataFrame representing context and child data

        Parameters
        ----------
        recursive : bool, optional
            Optional, specify False to export only the root context's data,
            ignoring any nested child data.

        """
        raise NotImplementedError


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

    def __init__(self, profile: ExportProfile, context: Exportable):
        self._profile = profile
        self._context = context

    @property
    def context(self) -> Exportable:
        return self._context

    @property
    def data(self) -> DataFrame:
        return self._context.export()

    @property
    def parameters(self):
        raise NotImplementedError

    @property
    def profile(self) -> ExportProfile:
        return self._profile

    def export(self, descriptor):
        raise NotImplementedError
