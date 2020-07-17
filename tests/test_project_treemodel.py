# -*- coding: utf-8 -*-
from PyQt5.QtTest import QSignalSpy

from dgp.core.oid import OID
from dgp.core.models.project import AirborneProject
from dgp.core.controllers.flight_controller import FlightController
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.core.controllers.project_treemodel import ProjectTreeModel


def test_ProjectTreeModel_init(project: AirborneProject,
                               prj_ctrl: AirborneProjectController):

    model = ProjectTreeModel(prj_ctrl)
    assert 1 == model.rowCount()
    assert prj_ctrl == model.active_project


def test_ProjectTreeModel_multiple_projects(project: AirborneProject,
                                            prj_ctrl: AirborneProjectController):
    prj_ctrl2 = AirborneProjectController(project)
    assert prj_ctrl is not prj_ctrl2

    model = ProjectTreeModel(prj_ctrl)
    assert 1 == model.rowCount()
    assert prj_ctrl == model.active_project

    model.add_project(prj_ctrl2)
    assert 2 == model.rowCount()
    assert prj_ctrl == model.active_project
    model.item_activated(model.index(prj_ctrl2.row(), 0))
    assert prj_ctrl2 == model.active_project

    assert prj_ctrl in model.projects
    assert prj_ctrl2 in model.projects

