# coding: utf-8
from datetime import datetime, date
from pathlib import Path

import pytest

from .context import APP

import PyQt5.QtTest as QtTest
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QDialogButtonBox

from dgp.core.models.flight import Flight
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.gui.dialog.add_gravimeter_dialog import AddGravimeterDialog
from dgp.gui.dialog.add_flight_dialog import AddFlightDialog
from dgp.core.models.project import AirborneProject
from dgp.gui.dialog.create_project_dialog import CreateProjectDialog


@pytest.fixture
def airborne_prj(tmpdir):
    project = AirborneProject(name="AirborneProject", path=Path(tmpdir))
    prj_ctrl = AirborneProjectController(project)
    return project, prj_ctrl


class TestDialogs:
    def test_create_project_dialog(self, tmpdir):
        dlg = CreateProjectDialog()
        _name = "Test Project"
        _notes = "Notes on the Test Project"
        _path = Path(tmpdir)

        QTest.keyClicks(dlg.prj_name, _name)
        assert _name == dlg.prj_name.text()

        assert str(Path().home().joinpath('Desktop')) == dlg.prj_dir.text()

        dlg.prj_dir.setText('')
        QTest.keyClicks(dlg.prj_dir, str(_path))
        assert str(_path) == dlg.prj_dir.text()

        QTest.keyClicks(dlg.qpte_notes, _notes)
        assert _notes == dlg.qpte_notes.toPlainText()

        QTest.mouseClick(dlg.btn_create, Qt.LeftButton)

        assert isinstance(dlg.project, AirborneProject)
        assert _path.joinpath("TestProject") == dlg.project.path
        assert dlg.project.name == "".join(_name.split(' '))
        assert dlg.project.description == _notes

    def test_add_flight_dialog(self, airborne_prj):
        project, project_ctrl = airborne_prj
        dlg = AddFlightDialog(project_ctrl)
        spy = QtTest.QSignalSpy(dlg.accepted)
        assert spy.isValid()
        assert 0 == len(spy)

        _name = "Flight-1"
        _notes = "Notes for Flight-1"

        assert datetime.today() == dlg.qde_flight_date.date()
        QTest.keyClicks(dlg.qle_flight_name, _name)
        QTest.keyClicks(dlg.qte_notes, _notes)

        assert _name == dlg.qle_flight_name.text()
        assert _notes == dlg.qte_notes.toPlainText()

        QTest.mouseClick(dlg.qdbb_dialog_btns.button(QDialogButtonBox.Ok), Qt.LeftButton)
        # dlg.accept()

        assert 1 == len(spy)
        assert 1 == len(project.flights)
        assert isinstance(project.flights[0], Flight)
        assert _name == project.flights[0].name
        assert _notes == project.flights[0].notes
        assert date.today() == project.flights[0].date

    def test_edit_flight_dialog(self, airborne_prj):
        """Test Flight Dialog to edit an existing flight"""
        project, project_ctrl = airborne_prj  # type: AirborneProject, AirborneProjectController

        _name = "Flt-1"
        _date = datetime(2018, 5, 15)
        _notes = "Notes on flight 1"
        flt = Flight(_name, date=_date, notes=_notes, sequence=0, duration=6)

        flt_ctrl = project_ctrl.add_child(flt)

        dlg = AddFlightDialog.from_existing(flt_ctrl, project_ctrl)

        assert _name == dlg.qle_flight_name.text()
        assert _date == dlg.qde_flight_date.date()
        assert _notes == dlg.qte_notes.toPlainText()

        # Test renaming flight through dialog
        dlg.qle_flight_name.clear()
        QTest.keyClicks(dlg.qle_flight_name, "Flt-2")
        QTest.mouseClick(dlg.qdbb_dialog_btns.button(QDialogButtonBox.Ok), Qt.LeftButton)
        # Note: use dlg.accept() for debugging as it will correctly generate a stack trace
        # dlg.accept()
        assert "Flt-2" == flt.name

    def test_add_gravimeter_dialog(self, airborne_prj):
        project, project_ctrl = airborne_prj
        dlg = AddGravimeterDialog(project_ctrl)

