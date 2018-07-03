# -*- coding: utf-8 -*-
from pathlib import Path

from dgp.core.models.flight import Flight
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.core.models.project import AirborneProject
from dgp.core.controllers.project_treemodel import ProjectTreeModel

from .context import APP


def test_project_treemodel(tmpdir):
    project = AirborneProject(name="TestProjectTreeModel", path=Path(tmpdir))
    project_ctrl = AirborneProjectController(project)

    flt1 = Flight("Flt1")
    fc1 = project_ctrl.add_child(flt1)

    model = ProjectTreeModel(project_ctrl)

    fc1_index = model.index(fc1.row(), 0, parent=model.index(project_ctrl.flights.row(), 0, parent=model.index(
        project_ctrl.row(), 0)))
    assert not fc1.is_active()
    model.on_double_click(fc1_index)
    assert fc1.is_active()

    prj_index = model.index(project_ctrl.row(), 0)
    assert model.on_double_click(prj_index) is None
