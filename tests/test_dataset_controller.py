# -*- coding: utf-8 -*-
from datetime import datetime
from pathlib import Path

import pytest
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from pandas import Timestamp, Timedelta, DataFrame

from dgp.core.hdf5_manager import HDF5Manager
from dgp.core import OID, DataType
from dgp.core.models.datafile import DataFile
from dgp.core.models.dataset import DataSet, DataSegment
from dgp.core.models.flight import Flight
from dgp.core.models.project import AirborneProject
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.core.controllers.dataset_controller import DataSetController, DataSegmentController


def test_dataset_controller(tmpdir):
    """Test DataSet controls
    Load data from HDF5 Store
    Behavior when incomplete (no grav or traj)
    """
    hdf = Path(tmpdir).joinpath('test.hdf5')
    prj = AirborneProject(name="TestPrj", path=Path(tmpdir))
    flt = Flight("TestFlt")
    grav_file = DataFile(DataType.GRAVITY, datetime.now(), Path(tmpdir).joinpath('gravity.dat'))
    traj_file = DataFile(DataType.TRAJECTORY, datetime.now(), Path(tmpdir).joinpath('trajectory.txt'))
    ds = DataSet(grav_file, traj_file)
    seg0 = DataSegment(OID(), Timestamp.now(), Timestamp.now() + Timedelta(minutes=30), 0)
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

    grav1_file = DataFile(DataType.GRAVITY, datetime.now(), Path(tmpdir).joinpath('gravity2.dat'))
    dsc.add_datafile(grav1_file)
    assert grav1_file == dsc.get_datafile(grav1_file.group).datamodel

    traj1_file = DataFile(DataType.TRAJECTORY, datetime.now(), Path(tmpdir).joinpath('traj2.txt'))
    dsc.add_datafile(traj1_file)
    assert traj1_file == dsc.get_datafile(traj1_file.group).datamodel

    invl_file = DataFile('marine', datetime.now(), Path(tmpdir))
    with pytest.raises(TypeError):
        dsc.add_datafile(invl_file)

    with pytest.raises(KeyError):
        dsc.get_datafile('marine')

    # Test Data Segment Features
    _seg_oid = OID(tag="seg1")
    _seg1_start = Timestamp.now()
    _seg1_stop = Timestamp.now() + Timedelta(hours=1)
    seg1_ctrl = dsc.add_segment(_seg_oid, _seg1_start, _seg1_stop, label="seg1")
    seg1: DataSegment = seg1_ctrl.datamodel
    assert _seg1_start == seg1.start
    assert _seg1_stop == seg1.stop
    assert "seg1" == seg1.label

    assert seg1_ctrl == dsc.get_segment(_seg_oid)
    assert isinstance(seg1_ctrl, DataSegmentController)
    assert "seg1" == seg1_ctrl.get_attr('label')
    assert _seg_oid == seg1_ctrl.uid

    assert 2 == len(ds.segments)
    assert ds.segments[1] == seg1_ctrl.datamodel
    assert ds.segments[1] == seg1_ctrl.data(Qt.UserRole)

    # Segment updates
    _new_start = Timestamp.now() + Timedelta(hours=2)
    _new_stop = Timestamp.now() + Timedelta(hours=3)
    dsc.update_segment(seg1.uid, _new_start, _new_stop)
    assert _new_start == seg1.start
    assert _new_stop == seg1.stop
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
    grav_file_ctrl = ds_ctrl.get_datafile(DataType.GRAVITY)
    gps_file = ds_ctrl.datamodel.trajectory
    gps_file_ctrl = ds_ctrl.get_datafile(DataType.TRAJECTORY)

    assert grav_file.uid == grav_file_ctrl.uid
    assert ds_ctrl == grav_file_ctrl.dataset
    assert grav_file.group == grav_file_ctrl.group

    assert gps_file.uid == gps_file_ctrl.uid
    assert ds_ctrl == gps_file_ctrl.dataset
    assert gps_file.group == gps_file_ctrl.group


# def test_dataset_reparenting(project: AirborneProject):
#     # Test reassignment of DataSet to another Flight
#     # Note: FlightController automatically adds empty DataSet if Flight has None
#     prj_ctrl = AirborneProjectController(project)
#     flt1ctrl = prj_ctrl.get_child(project.flights[0].uid)
#     flt2ctrl = prj_ctrl.get_child(project.flights[1].uid)
#     dsctrl = flt1ctrl.get_child(flt1ctrl.datamodel.datasets[0].uid)
#     assert isinstance(dsctrl, DataSetController)
#
#     assert 1 == len(flt1ctrl.datamodel.datasets)
#     assert 1 == flt1ctrl.rowCount()
#
#     assert 1 == len(flt2ctrl.datamodel.datasets)
#     assert 1 == flt2ctrl.rowCount()
#
#     assert flt1ctrl == dsctrl.get_parent()
#
#     dsctrl.set_parent(flt2ctrl)
#     assert 2 == flt2ctrl.rowCount()
#     assert 0 == flt1ctrl.rowCount()
#     assert flt2ctrl == dsctrl.get_parent()
#
#     # DataSetController is recreated when added to new flight.
#     assert not dsctrl == flt2ctrl.get_child(dsctrl.uid)
#     assert flt1ctrl.get_child(dsctrl.uid) is None


def test_dataset_data_api(project: AirborneProject, hdf5file, gravdata, gpsdata):
    prj_ctrl = AirborneProjectController(project)
    flt_ctrl = prj_ctrl.get_child(project.flights[0].uid)

    gravfile = DataFile(DataType.GRAVITY, datetime.now(),
                        Path('tests/sample_gravity.csv'))
    gpsfile = DataFile(DataType.TRAJECTORY, datetime.now(),
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

