# -*- coding: utf-8 -*-

# Test gui/main.py
import pytest
from PyQt5.QtWidgets import QMainWindow

from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.gui.main import MainWindow


@pytest.fixture
def pctrl(project):
    return AirborneProjectController(project)


def test_MainWindow_load(project):
    prj_ctrl = AirborneProjectController(project)
    window = MainWindow(prj_ctrl)

    assert isinstance(window, QMainWindow)
    assert not window.isVisible()
    assert prj_ctrl in window.projects

    window.load()
    assert window.isVisible()
    assert not window.isWindowModified()


