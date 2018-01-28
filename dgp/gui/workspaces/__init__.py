# coding: utf-8

from importlib import import_module

from dgp.lib.project import Flight
from dgp.lib.enums import DataTypes

from .BaseTab import BaseTab
from .LineTab import LineProcessTab
from .PlotTab import PlotTab
from .TransformTab import TransformTab

__all__ = ['BaseTab', 'LineProcessTab', 'PlotTab', 'TransformTab']

_modules = []
for name in ['BaseTab', 'LineTab', 'MapTab', 'PlotTab']:
    mod = import_module('.%s' % name, __name__)
    _modules.append(mod)

tabs = []
for mod in _modules:
    tab = [cls for cls in mod.__dict__.values() if isinstance(cls, BaseTab)]
    tabs.append(tab)
