# -*- coding: utf-8 -*-
from datetime import datetime
from pathlib import Path

import pytest
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QWidget, QMenu
from pandas import DataFrame, Timedelta, Timestamp

from dgp.core import DataType
from dgp.core.oid import OID
from dgp.core.hdf5_manager import HDF5Manager
from dgp.core.models.dataset import DataSet, DataSegment
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.core.models.project import AirborneProject
from dgp.core.controllers.controller_mixins import AttributeProxy
from dgp.core.controllers.controller_interfaces import IMeterController, AbstractController
from dgp.core.controllers.gravimeter_controller import GravimeterController
from dgp.core.controllers.dataset_controller import (DataSetController,
                                                     DataSegmentController)
from dgp.core.models.meter import Gravimeter
from dgp.core.models.datafile import DataFile
from dgp.core.controllers.flight_controller import FlightController
from dgp.core.models.flight import Flight


def test_attribute_proxy(tmpdir):
    _name = "TestPrj"
    _path = Path(tmpdir)
    prj = AirborneProject(name=_name, path=_path)
    prj_ctrl = AirborneProjectController(prj)

    assert _name == prj_ctrl.get_attr('name')

    # Test get_attr on non existent attribute
    with pytest.raises(AttributeError):
        prj_ctrl.get_attr('not_an_attr')

    # Test attribute write protect
    with pytest.raises(AttributeError):
        prj_ctrl.set_attr('path', Path('.'))

    # Test attribute validation
    with pytest.raises(ValueError):
        prj_ctrl.set_attr('name', '1prj')

    prj_ctrl.set_attr('name', 'ValidPrjName')


def test_gravimeter_controller(tmpdir):
    prj = AirborneProjectController(AirborneProject(name="TestPrj", path=Path(tmpdir)))
    meter = Gravimeter('AT1A-Test')
    meter_ctrl = GravimeterController(meter)

    assert isinstance(meter_ctrl, AbstractController)
    assert isinstance(meter_ctrl, IMeterController)
    assert isinstance(meter_ctrl, AttributeProxy)

    assert meter == meter_ctrl.data(Qt.UserRole)

    with pytest.raises(AttributeError):
        meter_ctrl.set_attr('invalid_attr', 1234)

    assert 'AT1A-Test' == meter_ctrl.get_attr('name')
    assert meter_ctrl.get_parent() is None
    meter_ctrl.set_parent(prj)
    assert prj == meter_ctrl.get_parent()

    assert hash(meter_ctrl)

    meter_ctrl_clone = meter_ctrl.clone()
    assert meter == meter_ctrl_clone.entity

    assert "AT1A-Test" == meter_ctrl.data(Qt.DisplayRole)
    meter_ctrl.set_attr('name', "AT1A-New")
    assert "AT1A-New" == meter_ctrl.data(Qt.DisplayRole)


def test_flight_controller(project: AirborneProject):
    prj_ctrl = AirborneProjectController(project)
    flight = Flight('Test-Flt-1')
    data0 = DataFile(DataType.TRAJECTORY, datetime(2018, 5, 10), Path('./data0.dat'))
    data1 = DataFile(DataType.GRAVITY, datetime(2018, 5, 15), Path('./data1.dat'))
    dataset = DataSet(data1, data0)
    # dataset.set_active(True)
    flight.datasets.append(dataset)

    _traj_data = [0, 1, 5, 9]
    _grav_data = [2, 8, 1, 0]
    # Load test data into temporary project HDFStore
    HDF5Manager.save_data(DataFrame(_traj_data), data0, path=prj_ctrl.hdfpath)
    HDF5Manager.save_data(DataFrame(_grav_data), data1, path=prj_ctrl.hdfpath)

    fc = prj_ctrl.add_child(flight)
    assert hash(fc)
    assert str(fc) == str(flight)
    assert flight.uid == fc.uid
    assert flight.name == fc.data(Qt.DisplayRole)

    dsc = fc.get_child(dataset.uid)
    assert isinstance(dsc, DataSetController)

    dataset2 = DataSet()
    dsc2 = fc.add_child(dataset2)
    assert isinstance(dsc2, DataSetController)

    with pytest.raises(TypeError):
        fc.add_child({1: "invalid child"})

    # fc.set_parent(None)

    with pytest.raises(KeyError):
        fc.remove_child("Not a real child", confirm=False)

    assert dsc2 == fc.get_child(dsc2.uid)
    assert fc.remove_child(dataset2.uid, confirm=False)
    assert fc.get_child(dataset2.uid) is None

    fc.remove_child(dsc.uid, confirm=False)
    assert 0 == len(fc.entity.datasets)


def test_FlightController_bindings(project: AirborneProject):
    prj_ctrl = AirborneProjectController(project)
    fc0 = prj_ctrl.get_child(project.flights[0].uid)

    assert isinstance(fc0, FlightController)

    # Validate menu bindings
    for binding in fc0.menu:
        assert 2 == len(binding)
        assert hasattr(QMenu, binding[0])

    assert fc0 == prj_ctrl.get_child(fc0.uid)
    fc0._action_delete_self(confirm=False)
    assert prj_ctrl.get_child(fc0.uid) is None


def test_airborne_project_controller(project):
    flt0 = Flight("Flt0")
    mtr0 = Gravimeter("AT1A-X")
    project.add_child(flt0)
    project.add_child(mtr0)

    assert 3 == len(project.flights)
    assert 2 == len(project.gravimeters)

    project_ctrl = AirborneProjectController(project)
    assert project == project_ctrl.entity
    assert project_ctrl.path == project.path
    # Need a model to have a parent
    assert project_ctrl.parent_widget is None

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
    assert project.name == project_ctrl.data(Qt.DisplayRole)
    assert str(project.path) == project_ctrl.data(Qt.ToolTipRole)
    assert project.uid == project_ctrl.uid

    assert isinstance(project_ctrl.meter_model, QStandardItemModel)
    assert isinstance(project_ctrl.flight_model, QStandardItemModel)

    project_ctrl.add_child(flight2)

    fc2 = project_ctrl.get_child(flight2.uid)
    assert isinstance(fc2, FlightController)
    assert flight2 == fc2.entity

    assert 5 == project_ctrl.flights.rowCount()
    project_ctrl.remove_child(flight2.uid, confirm=False)
    assert 4 == project_ctrl.flights.rowCount()
    assert project_ctrl.get_child(fc2.uid) is None

    assert 3 == project_ctrl.meters.rowCount()
    project_ctrl.remove_child(meter.uid, confirm=False)
    assert 2 == project_ctrl.meters.rowCount()

    with pytest.raises(KeyError):
        project_ctrl.remove_child("Not a child")

    jsons = project_ctrl.save(to_file=False)
    assert isinstance(jsons, str)

