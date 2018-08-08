# -*- coding: utf-8 -*-

# Tests for gui workspace widgets in gui/workspaces

import pytest
import pandas as pd

from dgp.core.controllers.dataset_controller import DataSetController
from dgp.core.models.project import AirborneProject
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.gui.workspaces import PlotTab


def test_plot_tab_init(project: AirborneProject):
    prj_ctrl = AirborneProjectController(project)
    flt1_ctrl = prj_ctrl.get_child(project.flights[0].uid)
    ds_ctrl = flt1_ctrl.get_child(flt1_ctrl.datamodel.datasets[0].uid)
    assert isinstance(ds_ctrl, DataSetController)
    assert ds_ctrl == flt1_ctrl.active_child
    assert pd.DataFrame().equals(ds_ctrl.dataframe())

    tab = PlotTab("TestTab", flt1_ctrl)
