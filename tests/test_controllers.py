# -*- coding: utf-8 -*-
from datetime import datetime
from pathlib import Path

import pytest
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QWidget, QMenu
from pandas import DataFrame

from dgp.core.oid import OID
from dgp.core.hdf5_manager import HDF5Manager
from dgp.core.models.dataset import DataSet, DataSegment
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.core.models.project import AirborneProject
from dgp.core.controllers.controller_mixins import AttributeProxy
from dgp.core.controllers.controller_interfaces import IChild, IMeterController, IParent
from dgp.core.controllers.gravimeter_controller import GravimeterController
from dgp.core.controllers.dataset_controller import (DataSetController,
                                                     DataSegmentController)
from dgp.core.models.meter import Gravimeter
from dgp.core.models.datafile import DataFile
from dgp.core.controllers.flight_controller import FlightController
from dgp.core.models.flight import Flight
from .context import APP


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

    assert isinstance(meter_ctrl, IChild)
    assert isinstance(meter_ctrl, IMeterController)
    assert isinstance(meter_ctrl, AttributeProxy)
    assert not isinstance(meter_ctrl, IParent)

    assert meter == meter_ctrl.data(Qt.UserRole)

    with pytest.raises(AttributeError):
        meter_ctrl.set_attr('invalid_attr', 1234)

    assert 'AT1A-Test' == meter_ctrl.get_attr('name')
    assert meter_ctrl.get_parent() is None
    meter_ctrl.set_parent(prj)
    assert prj == meter_ctrl.get_parent()

    assert hash(meter_ctrl)

    meter_ctrl_clone = meter_ctrl.clone()
    assert meter == meter_ctrl_clone.datamodel

    assert "AT1A-Test" == meter_ctrl.data(Qt.DisplayRole)
    meter_ctrl.set_attr('name', "AT1A-New")
    assert "AT1A-New" == meter_ctrl.data(Qt.DisplayRole)


def test_flight_controller(project: AirborneProject):
    prj_ctrl = AirborneProjectController(project)
    flight = Flight('Test-Flt-1')
    data0 = DataFile('trajectory', datetime(2018, 5, 10), Path('./data0.dat'))
    data1 = DataFile('gravity', datetime(2018, 5, 15), Path('./data1.dat'))
    dataset = DataSet(data1, data0)
    # dataset.set_active(True)
    flight.datasets.append(dataset)

    _traj_data = [0, 1, 5, 9]
    _grav_data = [2, 8, 1, 0]
    # Load test data into temporary project HDFStore
    HDF5Manager.save_data(DataFrame(_traj_data), data0, path=prj_ctrl.hdf5path)
    HDF5Manager.save_data(DataFrame(_grav_data), data1, path=prj_ctrl.hdf5path)

    fc = prj_ctrl.add_child(flight)
    assert hash(fc)
    assert str(fc) == str(flight)
    assert not fc.is_active
    prj_ctrl.activate_child(fc.uid)
    assert fc.is_active
    assert flight.uid == fc.uid
    assert flight.name == fc.data(Qt.DisplayRole)

    dsc = fc.get_child(dataset.uid)
    fc.activate_child(dsc.uid)
    assert isinstance(dsc, DataSetController)
    assert dsc == fc.active_child

    dataset2 = DataSet()
    dsc2 = fc.add_child(dataset2)
    assert isinstance(dsc2, DataSetController)

    with pytest.raises(TypeError):
        fc.add_child({1: "invalid child"})

    fc.activate_child(dsc.uid)
    assert dsc == fc.active_child

    fc.set_parent(None)

    with pytest.raises(KeyError):
        fc.remove_child("Not a real child", confirm=False)

    assert dsc2 == fc.get_child(dsc2.uid)
    assert fc.remove_child(dataset2.uid, confirm=False)
    assert fc.get_child(dataset2.uid) is None

    fc.remove_child(dsc.uid, confirm=False)
    assert 0 == len(fc.datamodel.datasets)
    assert fc.active_child is None


def test_FlightController_bindings(project: AirborneProject):
    prj_ctrl = AirborneProjectController(project)
    fc0 = prj_ctrl.get_child(project.flights[0].uid)

    assert isinstance(fc0, FlightController)

    # Validate menu bindings
    for binding in fc0.menu_bindings:
        assert 2 == len(binding)
        assert hasattr(QMenu, binding[0])

    assert prj_ctrl.active_child is None
    fc0._activate_self()
    assert fc0 == prj_ctrl.active_child
    assert fc0.is_active

    assert fc0 == prj_ctrl.get_child(fc0.uid)
    fc0._delete_self(confirm=False)
    assert prj_ctrl.get_child(fc0.uid) is None


def test_airborne_project_controller(project):
    flt0 = Flight("Flt0")
    mtr0 = Gravimeter("AT1A-X")
    project.add_child(flt0)
    project.add_child(mtr0)

    assert 3 == len(project.flights)
    assert 2 == len(project.gravimeters)

    project_ctrl = AirborneProjectController(project)
    assert project == project_ctrl.datamodel
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

    assert project_ctrl.active_child is None
    project_ctrl.activate_child(fc.uid)
    assert fc == project_ctrl.active_child
    # with pytest.raises(ValueError):
    #     project_ctrl.activate_child(mc)

    project_ctrl.add_child(flight2)

    fc2 = project_ctrl.get_child(flight2.uid)
    assert isinstance(fc2, FlightController)
    assert flight2 == fc2.datamodel

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


def test_dataset_controller(tmpdir):
    """Test DataSet controls
    Load data from HDF5 Store
    Behavior when incomplete (no grav or traj)
    """
    hdf = Path(tmpdir).joinpath('test.hdf5')
    prj = AirborneProject(name="TestPrj", path=Path(tmpdir))
    flt = Flight("TestFlt")
    grav_file = DataFile('gravity', datetime.now(), Path(tmpdir).joinpath('gravity.dat'))
    traj_file = DataFile('trajectory', datetime.now(), Path(tmpdir).joinpath('trajectory.txt'))
    ds = DataSet(grav_file, traj_file)
    seg0 = DataSegment(OID(), datetime.now().timestamp(), datetime.now().timestamp() + 5000, 0)
    ds.segments.append(seg0)

    flt.datasets.append(ds)
    prj.add_child(flt)

    prj_ctrl = AirborneProjectController(prj)
    fc0 = prj_ctrl.get_child(flt.uid)
    dsc: DataSetController = fc0.get_child(ds.uid)
    assert 1 == dsc._segments.rowCount()

    assert isinstance(dsc, DataSetController)
    assert fc0 == dsc.get_parent()
    assert grav_file == dsc.get_datafile(grav_file.group).datamodel
    assert traj_file == dsc.get_datafile(traj_file.group).datamodel

    grav1_file = DataFile('gravity', datetime.now(), Path(tmpdir).joinpath('gravity2.dat'))
    dsc.add_datafile(grav1_file)
    assert grav1_file == dsc.get_datafile(grav1_file.group).datamodel

    traj1_file = DataFile('trajectory', datetime.now(), Path(tmpdir).joinpath('traj2.txt'))
    dsc.add_datafile(traj1_file)
    assert traj1_file == dsc.get_datafile(traj1_file.group).datamodel

    invl_file = DataFile('marine', datetime.now(), Path(tmpdir))
    with pytest.raises(TypeError):
        dsc.add_datafile(invl_file)

    with pytest.raises(KeyError):
        dsc.get_datafile('marine')

    # Test Data Segment Features
    _seg_oid = OID(tag="seg1")
    _seg1_start = datetime.now().timestamp()
    _seg1_stop = datetime.now().timestamp() + 1500
    seg1_ctrl = dsc.add_segment(_seg_oid, _seg1_start, _seg1_stop, label="seg1")
    seg1: DataSegment = seg1_ctrl.datamodel
    assert datetime.fromtimestamp(_seg1_start) == seg1.start
    assert datetime.fromtimestamp(_seg1_stop) == seg1.stop
    assert "seg1" == seg1.label

    assert seg1_ctrl == dsc.get_segment(_seg_oid)
    assert isinstance(seg1_ctrl, DataSegmentController)
    assert "seg1" == seg1_ctrl.get_attr('label')
    assert _seg_oid == seg1_ctrl.uid

    assert 2 == len(ds.segments)
    assert ds.segments[1] == seg1_ctrl.datamodel
    assert ds.segments[1] == seg1_ctrl.data(Qt.UserRole)

    # Segment updates
    _new_start = datetime.now().timestamp() + 1500
    _new_stop = datetime.now().timestamp() + 3600
    dsc.update_segment(seg1.uid, _new_start, _new_stop)
    assert datetime.fromtimestamp(_new_start) == seg1.start
    assert datetime.fromtimestamp(_new_stop) == seg1.stop
    assert "seg1" == seg1.label

    dsc.update_segment(seg1.uid, label="seg1label")
    assert "seg1label" == seg1.label

    invalid_uid = OID()
    assert dsc.get_segment(invalid_uid) is None
    with pytest.raises(KeyError):
        dsc.remove_segment(invalid_uid)
    with pytest.raises(KeyError):
        dsc.update_segment(invalid_uid, label="RaiseError")

    assert 2 == len(ds.segments)
    dsc.remove_segment(seg1.uid)
    assert 1 == len(ds.segments)
    assert 1 == dsc._segments.rowCount()


def test_dataset_datafiles(project: AirborneProject):
    prj_ctrl = AirborneProjectController(project)
    flt_ctrl = prj_ctrl.get_child(project.flights[0].uid)
    ds_ctrl = flt_ctrl.get_child(flt_ctrl.datamodel.datasets[0].uid)

    grav_file = ds_ctrl.datamodel.gravity
    grav_file_ctrl = ds_ctrl.get_datafile('gravity')
    gps_file = ds_ctrl.datamodel.trajectory
    gps_file_ctrl = ds_ctrl.get_datafile('trajectory')

    assert grav_file.uid == grav_file_ctrl.uid
    assert ds_ctrl == grav_file_ctrl.dataset
    assert grav_file.group == grav_file_ctrl.group

    assert gps_file.uid == gps_file_ctrl.uid
    assert ds_ctrl == gps_file_ctrl.dataset
    assert gps_file.group == gps_file_ctrl.group


def test_dataset_reparenting(project: AirborneProject):
    # Test reassignment of DataSet to another Flight
    # Note: FlightController automatically adds empty DataSet if Flight has None
    prj_ctrl = AirborneProjectController(project)
    flt1ctrl = prj_ctrl.get_child(project.flights[0].uid)
    flt2ctrl = prj_ctrl.get_child(project.flights[1].uid)
    dsctrl = flt1ctrl.get_child(flt1ctrl.datamodel.datasets[0].uid)
    assert isinstance(dsctrl, DataSetController)

    assert 1 == len(flt1ctrl.datamodel.datasets)
    assert 1 == flt1ctrl.rowCount()

    assert 1 == len(flt2ctrl.datamodel.datasets)
    assert 1 == flt2ctrl.rowCount()

    assert flt1ctrl == dsctrl.get_parent()

    dsctrl.set_parent(flt2ctrl)
    assert 2 == flt2ctrl.rowCount()
    assert 0 == flt1ctrl.rowCount()
    assert flt2ctrl == dsctrl.get_parent()

    # DataSetController is recreated when added to new flight.
    assert not dsctrl == flt2ctrl.get_child(dsctrl.uid)
    assert flt1ctrl.get_child(dsctrl.uid) is None


def test_dataset_data_api(project: AirborneProject, hdf5file, gravdata, gpsdata):
    prj_ctrl = AirborneProjectController(project)
    flt_ctrl = prj_ctrl.get_child(project.flights[0].uid)

    gravfile = DataFile('gravity', datetime.now(),
                        Path('tests/sample_gravity.csv'))
    gpsfile = DataFile('trajectory', datetime.now(),
                       Path('tests/sample_trajectory.txt'), column_format='hms')

    dataset = DataSet(gravfile, gpsfile)

    HDF5Manager.save_data(gravdata, gravfile, hdf5file)
    HDF5Manager.save_data(gpsdata, gpsfile, hdf5file)

    dataset_ctrl = DataSetController(dataset, flt_ctrl)

    gravity_frame = HDF5Manager.load_data(gravfile, hdf5file)
    assert gravity_frame.equals(dataset_ctrl.gravity)

    trajectory_frame = HDF5Manager.load_data(gpsfile, hdf5file)
    assert trajectory_frame.equals(dataset_ctrl.trajectory)

    assert dataset_ctrl.dataframe() is not None
    expected: DataFrame = pd.concat([gravdata, gpsdata], axis=1, sort=True)
    for col in expected:
        pass
        # print(f'{col}: {expected[col][3]}')
    # print(f'{expected}')
    expected_cols = [col for col in expected]

    assert expected.equals(dataset_ctrl.dataframe())
    assert set(expected_cols) == set(dataset_ctrl.columns)

    series_model = dataset_ctrl.series_model
    assert isinstance(series_model, QStandardItemModel)
    assert len(expected_cols) == series_model.rowCount()

    for i in range(series_model.rowCount()):
        item: QStandardItem = series_model.item(i, 0)
        col = item.data(Qt.DisplayRole)
        series = item.data(Qt.UserRole)

        assert expected[col].equals(series)


def test_parent_child_activations(project: AirborneProject):
    """Test child/parent interaction of DataSet Controller with
    FlightController
    """
    prj_ctrl = AirborneProjectController(project)
    flt_ctrl = prj_ctrl.get_child(project.flights[0].uid)
    flt2 = Flight("Flt-2")
    flt2_ctrl = prj_ctrl.add_child(flt2)

    _ds_name = "DataSet-Test"
    dataset = DataSet(name=_ds_name)
    ds_ctrl = flt_ctrl.add_child(dataset)

    assert prj_ctrl is flt_ctrl.get_parent()
    assert flt_ctrl is ds_ctrl.get_parent()

    assert prj_ctrl.can_activate
    assert flt_ctrl.can_activate
    assert ds_ctrl.can_activate

    assert not prj_ctrl.is_active
    assert not flt_ctrl.is_active

    from dgp.core.types.enumerations import StateColor
    assert StateColor.INACTIVE.value == prj_ctrl.background().color().name()
    assert StateColor.INACTIVE.value == flt_ctrl.background().color().name()
    assert StateColor.INACTIVE.value == ds_ctrl.background().color().name()

    prj_ctrl.set_active(True)
    assert StateColor.ACTIVE.value == prj_ctrl.background().color().name()
    flt_ctrl.set_active(True)

    # Test exclusive/non-exclusive child activation
    assert flt_ctrl is prj_ctrl.active_child
    prj_ctrl.activate_child(flt2_ctrl.uid, exclusive=False)
    assert flt_ctrl.is_active
    assert flt2_ctrl.is_active

    prj_ctrl.activate_child(flt2_ctrl.uid, exclusive=True)
    assert flt2_ctrl.is_active
    assert not flt_ctrl.is_active






