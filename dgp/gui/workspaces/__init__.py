# -*- coding: utf-8 -*-
from dgp.core.controllers.controller_interfaces import IBaseController
from .project import ProjectTab, AirborneProjectController
from .flight import FlightTab, FlightController
from .dataset import DataSetTab, DataSetController

__all__ = ['ProjectTab', 'FlightTab', 'DataSetTab', 'tab_factory']

_tabmap = {AirborneProjectController: ProjectTab,
           FlightController: FlightTab,
           DataSetController: DataSetTab}


def tab_factory(controller: IBaseController):
    """Return the workspace tab constructor for the given controller type"""
    return _tabmap.get(controller.__class__, None)

