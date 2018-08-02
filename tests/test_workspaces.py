# -*- coding: utf-8 -*-

# Tests for gui workspace widgets in gui/workspaces

import pytest
import pandas as pd

from dgp.core.controllers.dataset_controller import DataSetController
from dgp.core.models.project import AirborneProject
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.gui.workspaces import PlotTab
from dgp.gui.workspaces.TransformTab import TransformWidget, _Mode


def test_plot_tab_init(project: AirborneProject):
    prj_ctrl = AirborneProjectController(project)
    flt1_ctrl = prj_ctrl.get_child(project.flights[0].uid)
    ds_ctrl = flt1_ctrl.get_child(flt1_ctrl.datamodel.datasets[0].uid)
    assert isinstance(ds_ctrl, DataSetController)
    assert ds_ctrl == flt1_ctrl.active_child
    assert pd.DataFrame().equals(ds_ctrl.dataframe())

    ptab = PlotTab("TestTab", flt1_ctrl)


def test_TransformTab_modes(prj_ctrl, flt_ctrl, gravdata):
    ttab = TransformWidget(flt_ctrl)

    assert ttab._mode is _Mode.NORMAL
    ttab.qpb_toggle_mode.click()
    assert ttab._mode is _Mode.SEGMENTS
    ttab.qpb_toggle_mode.click()
    assert ttab._mode is _Mode.NORMAL

    assert 0 == len(ttab._plot.get_plot(0).curves)
    ttab._add_series(gravdata['gravity'])
    assert 1 == len(ttab._plot.get_plot(0).curves)
    ttab._remove_series(gravdata['gravity'])
    assert 0 == len(ttab._plot.get_plot(0).curves)
