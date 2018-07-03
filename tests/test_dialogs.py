# coding: utf-8
from datetime import datetime, date
from pathlib import Path

import pytest


import PyQt5.QtTest as QtTest
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QDialogButtonBox

from dgp.core.controllers.flight_controller import FlightController
from dgp.core.models.data import DataFile
from dgp.core.models.flight import Flight
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.core.models.project import AirborneProject
from dgp.core.types.enumerations import DataTypes
from dgp.gui.dialogs.add_gravimeter_dialog import AddGravimeterDialog
from dgp.gui.dialogs.add_flight_dialog import AddFlightDialog
from dgp.gui.dialogs.data_import_dialog import DataImportDialog
from dgp.gui.dialogs.create_project_dialog import CreateProjectDialog
from .context import APP


@pytest.fixture
def airborne_prj(tmpdir):
    project = AirborneProject(name="AirborneProject", path=Path(tmpdir))
    prj_ctrl = AirborneProjectController(project)
    return project, prj_ctrl


class TestDialogs:
    def test_create_project_dialog(self, tmpdir):
        dlg = CreateProjectDialog()
        accept_spy = QtTest.QSignalSpy(dlg.accepted)
        _name = "Test Project"
        _notes = "Notes on the Test Project"
        _path = Path(tmpdir)

        # Test field validation
        assert str(Path().home().joinpath('Desktop')) == dlg.prj_dir.text()
        _invld_style = 'color: red'
        assert dlg.accept() is None
        assert _invld_style == dlg.label_name.styleSheet()
        dlg.prj_name.setText("TestProject")
        dlg.prj_dir.setText("")
        dlg.accept()
        assert 0 == len(dlg.prj_dir.text())
        assert _invld_style == dlg.label_dir.styleSheet()
        assert 0 == len(accept_spy)

        # Validate project directory exists
        dlg.prj_dir.setText(str(Path().joinpath("fake")))
        dlg.accept()
        assert 0 == len(accept_spy)

        dlg.prj_name.setText("")
        QTest.keyClicks(dlg.prj_name, _name)
        assert _name == dlg.prj_name.text()

        dlg.prj_dir.setText('')
        QTest.keyClicks(dlg.prj_dir, str(_path))
        assert str(_path) == dlg.prj_dir.text()

        QTest.keyClicks(dlg.qpte_notes, _notes)
        assert _notes == dlg.qpte_notes.toPlainText()

        QTest.mouseClick(dlg.btn_create, Qt.LeftButton)
        assert 1 == len(accept_spy)

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

    def test_import_data_dialog(self, airborne_prj, tmpdir):
        _path = Path(tmpdir).joinpath('source')
        _path.mkdir()
        project, project_ctrl = airborne_prj  # type: AirborneProject, AirborneProjectController
        _f1_date = datetime(2018, 3, 15)
        flt1 = Flight("Flight1", _f1_date)
        flt2 = Flight("Flight2")
        fc1 = project_ctrl.add_child(flt1)  # type: FlightController
        fc2 = project_ctrl.add_child(flt2)

        dlg = DataImportDialog(project_ctrl, datatype=DataTypes.GRAVITY)
        load_spy = QtTest.QSignalSpy(dlg.load)

        # test set_initial_flight
        dlg.set_initial_flight(fc1)
        assert flt1.name == dlg.qcb_flight.currentText()

        fc_clone = dlg._flight_model.item(dlg.qcb_flight.currentIndex())
        assert isinstance(fc_clone, FlightController)
        assert fc1 != fc_clone
        assert fc1 == dlg.flight

        assert dlg.file_path is None
        _srcpath = _path.joinpath('testfile.dat')
        QTest.keyClicks(dlg.qle_filepath, str(_srcpath))
        assert _srcpath == dlg.file_path

        dlg.qchb_grav_interp.setChecked(True)
        assert dlg.qchb_grav_interp.isChecked()
        _grav_map = dlg._params_map[DataTypes.GRAVITY]
        assert _grav_map['columns']() is None
        assert _grav_map['interp']()
        assert not _grav_map['skiprows']()

        _traj_map = dlg._params_map[DataTypes.TRAJECTORY]
        _time_col_map = {
            'hms': ['mdy', 'hms', 'lat', 'long', 'ell_ht'],
            'sow': ['week', 'sow', 'lat', 'long', 'ell_ht'],
            'serial': ['datenum', 'lat', 'long', 'ell_ht']
        }
        for i, expected in enumerate(['hms', 'sow', 'serial']):
            dlg.qcb_traj_timeformat.setCurrentIndex(i)
            assert expected == _traj_map['timeformat']()
            assert _time_col_map[expected] == _traj_map['columns']()

        assert not dlg.qchb_traj_hasheader.isChecked()
        assert 0 == _traj_map['skiprows']()
        dlg.qchb_traj_hasheader.setChecked(True)
        assert 1 == _traj_map['skiprows']()
        assert dlg.qchb_traj_isutc.isChecked()
        assert _traj_map['is_utc']()
        dlg.qchb_traj_isutc.setChecked(False)
        assert not _traj_map['is_utc']()

        # Test emission of DataFile on _load_file
        assert dlg.datatype == DataTypes.GRAVITY
        assert 0 == len(flt1.data_files)
        dlg._load_file()
        assert 1 == len(load_spy)
        assert 1 == len(flt1.data_files)
        assert _srcpath == flt1.data_files[0].source_path

        load_args = load_spy[0]
        assert isinstance(load_args, list)
        file = load_args[0]
        params = load_args[1]
        assert isinstance(file, DataFile)
        assert isinstance(params, dict)

        # Test date setting from flight
        assert datetime.today() == dlg.qde_date.date()
        dlg._set_date()
        assert _f1_date == dlg.qde_date.date()

        # Create the test DataFile to permit accept()
        _srcpath.touch()
        dlg.qchb_copy_file.setChecked(True)
        QTest.mouseClick(dlg.qdbb_buttons.button(QDialogButtonBox.Ok), Qt.LeftButton)
        # dlg.accept()
        assert 2 == len(load_spy)
        assert project_ctrl.path.joinpath('testfile.dat').exists()

    def test_add_gravimeter_dialog(self, airborne_prj):
        project, project_ctrl = airborne_prj  # type: AirborneProject, AirborneProjectController
        _basepath = project_ctrl.path.joinpath('source').resolve()
        _basepath.mkdir()

        dlg = AddGravimeterDialog(project_ctrl)
        assert dlg.config_path is None

        _ini_path = Path('tests/at1m.ini').resolve()
        QTest.keyClicks(dlg.qle_config_path, str(_ini_path))
        assert _ini_path == dlg.config_path

        # Test exclusion of invalid file extensions
        _bad_ini = _basepath.joinpath("meter.bad").resolve()
        _bad_ini.touch()
        dlg.qle_config_path.setText(str(_bad_ini))
        assert dlg.config_path is None
        assert dlg._preview_config() is None

        _name = "AT1A-11"
        assert "AT1A" == dlg.get_sensor_type()
        QTest.keyClicks(dlg.qle_serial, str(11))
        assert _name == dlg.qle_name.text()

        assert 0 == len(project.gravimeters)
        dlg.qle_config_path.setText(str(_ini_path.resolve()))
        dlg.accept()
        assert 1 == len(project.gravimeters)
        assert _name == project.gravimeters[0].name

        dlg2 = AddGravimeterDialog(project_ctrl)
        dlg2.qle_serial.setText(str(12))
        dlg2.accept()
        assert 2 == len(project.gravimeters)
        assert "AT1A-12" == project.gravimeters[1].name









