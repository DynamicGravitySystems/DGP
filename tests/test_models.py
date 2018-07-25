# -*- coding: utf-8 -*-

"""
Unit tests for new Project/Flight data classes, including JSON
serialization/de-serialization
"""
import time
from datetime import datetime
from typing import Tuple
from uuid import uuid4
from pathlib import Path

import pytest
import pandas as pd

from dgp.core.models.project import AirborneProject
from dgp.core.hdf5_manager import HDF5Manager
from dgp.core.models.datafile import DataFile
from dgp.core.models.dataset import DataSet
from dgp.core.models import flight
from dgp.core.models.meter import Gravimeter


@pytest.fixture()
def make_flight():
    def _factory() -> Tuple[str, flight.Flight]:
        name = str(uuid4().hex)[:12]
        return name, flight.Flight(name)

    return _factory


def test_flight_actions(make_flight):
    # TODO: Test adding/setting gravimeter
    flt = flight.Flight('test_flight')
    assert 'test_flight' == flt.name

    f1_name, f1 = make_flight()  # type: flight.Flight
    f2_name, f2 = make_flight()  # type: flight.Flight

    assert f1_name == f1.name
    assert f2_name == f2.name

    assert not f1.uid == f2.uid

    assert '<Flight %s :: %s>' % (f1_name, f1.uid) == repr(f1)


def test_project_path(project: AirborneProject, tmpdir):
    assert isinstance(project.path, Path)
    new_path = Path(tmpdir).joinpath("new_prj_path")
    project.path = new_path
    assert new_path == project.path


def test_project_add_child(project: AirborneProject):
    with pytest.raises(TypeError):
        project.add_child(None)


def test_project_get_child(make_flight):
    prj = AirborneProject(name="Project-2", path=Path('.'))
    f1_name, f1 = make_flight()
    f2_name, f2 = make_flight()
    f3_name, f3 = make_flight()
    prj.add_child(f1)
    prj.add_child(f2)
    prj.add_child(f3)

    assert f1 == prj.get_child(f1.uid)
    assert f3 == prj.get_child(f3.uid)
    assert not f2 == prj.get_child(f1.uid)

    with pytest.raises(IndexError):
        fx = prj.get_child(str(uuid4().hex))


def test_project_remove_child(make_flight):
    prj = AirborneProject(name="Project-3", path=Path('.'))
    f1_name, f1 = make_flight()
    f2_name, f2 = make_flight()
    f3_name, f3 = make_flight()

    prj.add_child(f1)
    prj.add_child(f2)

    assert 2 == len(prj.flights)
    assert f1 in prj.flights
    assert f2 in prj.flights
    assert f3 not in prj.flights

    assert not prj.remove_child(f3.uid)
    assert prj.remove_child(f1.uid)

    assert f1 not in prj.flights
    assert 1 == len(prj.flights)


def test_gravimeter():
    meter = Gravimeter("AT1A-13")
    assert "AT1A" == meter.type
    assert "AT1A-13" == meter.name
    assert meter.config is None
    config = meter.read_config(Path("tests/at1m.ini"))
    assert isinstance(config, dict)

    with pytest.raises(FileNotFoundError):
        config = meter.read_config(Path("tests/at1a-fake.ini"))

    assert {} == meter.read_config(Path("tests/sample_gravity.csv"))


def test_dataset(tmpdir):
    path = Path(tmpdir).joinpath("test.hdf5")
    df_grav = DataFile('gravity', datetime.utcnow(), Path('gravity.dat'))
    df_traj = DataFile('trajectory', datetime.utcnow(), Path('gps.dat'))
    dataset = DataSet(path, df_grav, df_traj)

    assert df_grav == dataset.gravity
    assert df_traj == dataset.trajectory

    frame_grav = pd.DataFrame([0, 1, 2])
    frame_traj = pd.DataFrame([7, 8, 9])

    HDF5Manager.save_data(frame_grav, df_grav, path)
    HDF5Manager.save_data(frame_traj, df_traj, path)

    expected_concat: pd.DataFrame = pd.concat([frame_grav, frame_traj])
    assert expected_concat.equals(dataset.dataframe)


