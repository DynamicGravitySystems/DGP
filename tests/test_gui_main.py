# -*- coding: utf-8 -*-

# Test gui/main.py
import logging
from pathlib import Path

import pytest
from PyQt5.QtTest import QSignalSpy
from PyQt5.QtWidgets import QMainWindow, QFileDialog

from dgp.core.models.project import AirborneProject
from dgp.core.controllers.project_treemodel import ProjectTreeModel
from dgp.core.controllers.flight_controller import FlightController
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.gui.main import MainWindow
from dgp.gui.workspace import WorkspaceTab
from dgp.gui.dialogs.create_project_dialog import CreateProjectDialog


@pytest.fixture
def flt_ctrl(prj_ctrl: AirborneProjectController):
    return prj_ctrl.get_child(prj_ctrl.datamodel.flights[0].uid)


@pytest.fixture
def window(prj_ctrl):
    return MainWindow(prj_ctrl)


def test_MainWindow_load(window):
    assert isinstance(window, QMainWindow)
    assert not window.isVisible()

    window.load()
    assert window.isVisible()
    assert not window.isWindowModified()

    window.close()
    assert not window.isVisible()


def test_MainWindow_tab_open_requested(flt_ctrl: FlightController,
                                       window: MainWindow):
    assert isinstance(window.model, ProjectTreeModel)

    tab_open_spy = QSignalSpy(window.model.tabOpenRequested)
    assert 0 == len(tab_open_spy)
    assert 0 == len(window._open_tabs)

    assert isinstance(flt_ctrl, FlightController)
    assert flt_ctrl.uid not in window._open_tabs

    window.model.active_changed(flt_ctrl)
    assert 1 == len(tab_open_spy)
    assert 1 == len(window._open_tabs)
    assert 1 == window.workspace.count()
    assert isinstance(window.workspace.currentWidget(), WorkspaceTab)

    window.model.active_changed(flt_ctrl)
    assert 2 == len(tab_open_spy)
    assert 1 == len(window._open_tabs)
    assert 1 == window.workspace.count()


def test_MainWindow_tab_close_requested(flt_ctrl: AirborneProjectController,
                                        window: MainWindow):
    tab_close_spy = QSignalSpy(window.model.tabCloseRequested)
    assert 0 == len(tab_close_spy)
    assert 0 == len(window._open_tabs)
    assert 0 == window.workspace.count()

    window.model.active_changed(flt_ctrl)
    assert 1 == window.workspace.count()

    window.model.close_flight(flt_ctrl)
    assert 1 == len(tab_close_spy)
    assert flt_ctrl.uid == tab_close_spy[0][0]
    assert flt_ctrl.uid not in window._open_tabs

    window.model.active_changed(flt_ctrl)
    assert 1 == window.workspace.count()
    assert flt_ctrl.uid in window._open_tabs
    window.workspace.tabCloseRequested.emit(0)
    assert 0 == window.workspace.count()

    assert 1 == len(tab_close_spy)
    window.model.close_flight(flt_ctrl)
    assert 2 == len(tab_close_spy)


def test_MainWindow_project_mutated(window: MainWindow):
    assert not window.isWindowModified()
    window.model.projectMutated.emit()
    assert window.isWindowModified()
    window.save_projects()
    assert not window.isWindowModified()


def test_MainWindow_set_logging_level(window: MainWindow):
    # Test UI combo-box widget to change/set logging level
    assert logging.DEBUG == window.log.level

    index_level_map = {0: logging.DEBUG,
                       1: logging.INFO,
                       2: logging.WARNING,
                       3: logging.ERROR,
                       4: logging.CRITICAL}

    for index, level in index_level_map.items():
        window.combo_console_verbosity.setCurrentIndex(index)
        assert level == window.log.level


def test_MainWindow_new_project_dialog(window: MainWindow, tmpdir):
    assert 1 == window.model.rowCount()
    dest = Path(tmpdir)
    dest_str = str(dest.absolute().resolve())

    dlg: CreateProjectDialog = window.new_project_dialog()
    projectCreated_spy = QSignalSpy(dlg.sigProjectCreated)
    dlg.prj_name.setText("TestNewProject")
    dlg.prj_dir.setText(dest_str)
    dlg.accept()

    assert 1 == len(projectCreated_spy)
    assert 2 == window.model.rowCount()

    prj_dir = dest.joinpath(dlg.project.name)
    assert prj_dir.exists()


def test_MainWindow_open_project_dialog(window: MainWindow, project_factory, tmpdir):
    prj2: AirborneProject = project_factory("Proj2", tmpdir, dataset=False)
    prj2_ctrl = AirborneProjectController(prj2)
    prj2_ctrl.save()
    prj2_ctrl.hdf5path.touch(exist_ok=True)

    assert window.project_.path != prj2_ctrl.path
    assert 1 == window.model.rowCount()

    window.open_project_dialog(path=prj2.path)
    assert 2 == window.model.rowCount()

    # Try to open an already open project
    window.open_project_dialog(path=prj2.path)
    assert 2 == window.model.rowCount()

    window.open_project_dialog(path=tmpdir)
    assert 2 == window.model.rowCount()
