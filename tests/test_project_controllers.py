# -*- coding: utf-8 -*-
import random
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from PyQt5.QtCore import Qt, QAbstractItemModel
from PyQt5.QtGui import QStandardItemModel
from pandas import DataFrame

from core.hdf5_manager import HDF5Manager
from core.models.dataset import DataSet
from dgp.core.controllers.flightline_controller import FlightLineController
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.core.models.project import AirborneProject
from dgp.core.controllers.controller_mixins import AttributeProxy
from dgp.core.controllers.controller_interfaces import IChild, IMeterController, IParent
from dgp.core.controllers.gravimeter_controller import GravimeterController
from dgp.core.controllers.dataset_controller import DataSetController
from dgp.core.models.meter import Gravimeter
from dgp.core.controllers.datafile_controller import DataFileController
from dgp.core.models.data import DataFile
from dgp.core.controllers.flight_controller import FlightController, LoadError
from dgp.core.models.flight import Flight, FlightLine
from .context import APP


@pytest.fixture
def project(tmpdir):
    prj = AirborneProject(name=str(uuid.uuid4()), path=Path(tmpdir))
    prj_ctrl = AirborneProjectController(prj)
    return prj_ctrl


@pytest.fixture()
def make_line():
    seq = 0

    def _factory():
        nonlocal seq
        seq += 1
        return FlightLine(datetime.now().timestamp(),
                          datetime.now().timestamp() + round(random.random() * 1000),
                          seq)
    return _factory


def test_flightline_controller():
    pass


# TODO: Rewrite this
def test_datafile_controller():
    flight = Flight('test_flightline_controller')
    fl_controller = FlightController(flight)
    # TODO: Deprecated, DataFiles cannot be children
    # datafile = DataFile('gravity', datetime(2018, 6, 15),
    #                     source_path=Path('c:\\data\\gravity.dat'))
    # fl_controller.add_child(datafile)

    # assert datafile in flight.data_files

    # assert isinstance(fl_controller._data_files.child(0), DataFileController)


def test_gravimeter_controller(tmpdir):
    project = AirborneProjectController(AirborneProject(name="TestPrj", path=Path(tmpdir)))
    meter = Gravimeter('AT1A-Test')
    meter_ctrl = GravimeterController(meter)

    assert isinstance(meter_ctrl, IChild)
    assert isinstance(meter_ctrl, IMeterController)
    assert isinstance(meter_ctrl, AttributeProxy)
    assert not isinstance(meter_ctrl, IParent)

    assert meter == meter_ctrl.data(Qt.UserRole)

    with pytest.raises(AttributeError):
        meter_ctrl.set_attr('invalid_attr', 1234)

    assert 'AT1A-Test' == meter_ctrl.get_attr('name')
    assert meter_ctrl.get_parent() is None
    meter_ctrl.set_parent(project)
    assert project == meter_ctrl.get_parent()

    assert hash(meter_ctrl)

    meter_ctrl_clone = meter_ctrl.clone()
    assert meter == meter_ctrl_clone.datamodel

    assert "AT1A-Test" == meter_ctrl.data(Qt.DisplayRole)
    meter_ctrl.set_attr('name', "AT1A-New")
    assert "AT1A-New" == meter_ctrl.data(Qt.DisplayRole)


def test_flight_controller(make_line, project: AirborneProjectController):
    flight = Flight('Test-Flt-1')
    line0 = make_line()
    data0 = DataFile('trajectory', datetime(2018, 5, 10), Path('./data0.dat'))
    data1 = DataFile('gravity', datetime(2018, 5, 15), Path('./data1.dat'))
    flight.add_child(line0)
    flight.add_child(data0)
    flight.add_child(data1)

    _traj_data = [0, 1, 5, 9]
    _grav_data = [2, 8, 1, 0]
    # Load test data into temporary project HDFStore
    HDF5Manager.save_data(DataFrame(_traj_data), data0, path=project.hdf5path)
    HDF5Manager.save_data(DataFrame(_grav_data), data1, path=project.hdf5path)
    # project.hdf5store.save_data(DataFrame(_traj_data), data0)
    # project.hdf5store.save_data(DataFrame(_grav_data), data1)

    # assert data0 in flight.data_files
    # assert data1 in flight.data_files
    # assert 1 == len(flight.flight_lines)
    # assert 2 == len(flight.data_files)

    fc = project.add_child(flight)
    assert hash(fc)
    assert str(fc) == str(flight)
    assert not fc.is_active()
    project.set_active_child(fc)
    assert fc.is_active()

    assert flight.uid == fc.uid
    assert flight.name == fc.data(Qt.DisplayRole)

    # assert fc._active_gravity is not None
    # assert fc._active_trajectory is not None
    # assert DataFrame(_traj_data).equals(fc.trajectory)
    # assert DataFrame(_grav_data).equals(fc.gravity)

    # line1 = make_line()
    # line2 = make_line()
    #
    # assert fc.add_child(line1)
    # assert fc.add_child(line2)

    # The data doesn't exist for this DataFile
    data2 = DataFile('gravity', datetime(2018, 5, 25), Path('./data2.dat'))
    data2_ctrl = fc.add_child(data2)
    assert isinstance(data2_ctrl, DataFileController)
    fc.set_active_child(data2_ctrl)
    assert fc.get_active_child() != data2_ctrl

    # assert line1 in flight.flight_lines
    # assert line2 in flight.flight_lines

    assert data2 in flight.data_files

    model = fc.lines_model
    assert isinstance(model, QAbstractItemModel)
    assert 3 == model.rowCount()

    # lines = [line0, line1, line2]
    # for i in range(model.rowCount()):
    #     index = model.index(i, 0)
    #     child = model.data(index, Qt.UserRole)
    #     assert lines[i] == child
    #
    # Test use of lines generator
    # for i, line in enumerate(fc.lines):
    #     assert lines[i] == line

    with pytest.raises(TypeError):
        fc.add_child({1: "invalid child"})

    with pytest.raises(TypeError):
        fc.set_active_child("not a child")

    fc.set_parent(None)
    # with pytest.raises(LoadError):
    #     fc.load_data(data0)

    # Test child removal
    # line1_ctrl = fc.get_child(line1.uid)
    # assert isinstance(line1_ctrl, FlightLineController)
    # assert line1.uid == line1_ctrl.uid
    # data1_ctrl = fc.get_child(data1.uid)
    # assert isinstance(data1_ctrl, DataFileController)
    # assert data1.uid == data1_ctrl.uid
    #
    # assert 3 == len(list(fc.lines))
    # assert line1 in flight.flight_lines
    # fc.remove_child(line1, line1_ctrl.row(), confirm=False)
    # assert 2 == len(list(fc.lines))
    # assert line1 not in flight.flight_lines
    #
    # assert 3 == fc._data_files.rowCount()
    # assert data1 in flight.data_files
    # fc.remove_child(data1, data1_ctrl.row(), confirm=False)
    # assert 2 == fc._data_files.rowCount()
    # assert data1 not in flight.data_files

    with pytest.raises(TypeError):
        fc.remove_child("Not a real child", 1, confirm=False)


def test_airborne_project_controller(tmpdir):
    _name = str(uuid.uuid4().hex)
    _path = Path(tmpdir).resolve()
    flt0 = Flight("Flt0")
    mtr0 = Gravimeter("AT1A-X")
    project = AirborneProject(name=_name, path=_path)
    project.add_child(flt0)
    project.add_child(mtr0)

    assert 1 == len(project.flights)
    assert 1 == len(project.gravimeters)

    project_ctrl = AirborneProjectController(project)
    assert project == project_ctrl.datamodel
    assert project_ctrl.path == project.path

    project_ctrl.set_parent_widget(APP)
    assert APP == project_ctrl.get_parent_widget()

    flight = Flight("Flt1")
    flight2 = Flight("Flt2")
    meter = Gravimeter("AT1A-10")

    fc = project_ctrl.add_child(flight)
    assert isinstance(fc, FlightController)
    assert flight in project.flights
    mc = project_ctrl.add_child(meter)
    assert isinstance(mc, GravimeterController)
    assert meter in project.gravimeters

    with pytest.raises(ValueError):
        project_ctrl.add_child("Invalid Child Object (Str)")

    assert project == project_ctrl.data(Qt.UserRole)
    assert _name == project_ctrl.data(Qt.DisplayRole)
    assert str(_path) == project_ctrl.data(Qt.ToolTipRole)
    assert project.uid == project_ctrl.uid
    assert _path == project.path

    assert isinstance(project_ctrl.meter_model, QStandardItemModel)
    assert isinstance(project_ctrl.flight_model, QStandardItemModel)

    assert project_ctrl.get_active_child() is None
    project_ctrl.set_active_child(fc)
    assert fc == project_ctrl.get_active_child()
    with pytest.raises(ValueError):
        project_ctrl.set_active_child(mc)

    project_ctrl.add_child(flight2)

    fc2 = project_ctrl.get_child(flight2.uid)
    assert isinstance(fc2, FlightController)
    assert flight2 == fc2.datamodel

    assert 3 == project_ctrl.flights.rowCount()
    project_ctrl.remove_child(flight2, fc2.row(), confirm=False)
    assert 2 == project_ctrl.flights.rowCount()
    assert project_ctrl.get_child(fc2.uid) is None

    assert 2 == project_ctrl.meters.rowCount()
    project_ctrl.remove_child(meter, mc.row(), confirm=False)
    assert 1 == project_ctrl.meters.rowCount()

    with pytest.raises(ValueError):
        project_ctrl.remove_child("Not a child", 2)

    jsons = project_ctrl.save(to_file=False)
    assert isinstance(jsons, str)


def test_dataset_controller(tmpdir):
    """Test DataSet controls
    Load data from HDF5 Store
    Behavior when incomplete (no grav or traj)
    """
    hdf = Path(tmpdir).joinpath('test.hdf5')
    ds = DataSet(hdf)
    dsc = DataSetController(ds)






