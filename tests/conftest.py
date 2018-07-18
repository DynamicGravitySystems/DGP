# -*- coding: utf-8 -*-
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from dgp.core.hdf5_manager import HDF5_NAME
from dgp.core.models.data import DataFile
from dgp.core.models.dataset import DataSegment, DataSet
from dgp.core.models.flight import Flight
from dgp.core.models.meter import Gravimeter
from dgp.core.models.project import AirborneProject
from dgp.core.oid import OID
from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.trajectory_ingestor import import_trajectory

# Import QApplication object for any Qt GUI test cases
from .context import APP


def get_ts(offset=0):
    return datetime.now().timestamp() + offset


@pytest.fixture()
def project(tmpdir):
    """This fixture constructs a project model with a flight, gravimeter,
    DataSet (and its children - DataFile/DataSegment) for testing the serialization
    and de-serialization of a fleshed out project.
    """
    base_dir = Path(tmpdir)
    prj = AirborneProject(name="TestProject", path=base_dir.joinpath("prj"),
                          description="Description of TestProject")
    prj.path.mkdir()

    flt1 = Flight("Flt1", sequence=0, duration=4)
    flt2 = Flight("Flt2", sequence=1, duration=6)

    mtr = Gravimeter.from_ini(Path('tests').joinpath('at1m.ini'), name="AT1A-X")

    grav1 = DataFile('gravity', datetime.now(), base_dir.joinpath('gravity1.dat'))
    traj1 = DataFile('trajectory', datetime.now(), base_dir.joinpath('gps1.dat'))
    seg1 = DataSegment(OID(), get_ts(0), get_ts(1500), 0, "seg1")
    seg2 = DataSegment(OID(), get_ts(1501), get_ts(3000), 1, "seg2")

    dataset1 = DataSet(prj.path.joinpath('hdfstore.hdf5'), grav1, traj1,
                       [seg1, seg2])

    flt1.datasets.append(dataset1)
    prj.add_child(mtr)
    prj.add_child(flt1)
    prj.add_child(flt2)
    return prj


@pytest.fixture(scope='module')
def hdf5file(tmpdir_factory) -> Path:
    file = Path(tmpdir_factory.mktemp("dgp")).joinpath(HDF5_NAME)
    file.touch(exist_ok=True)
    return file


@pytest.fixture(scope='session')
def gravdata() -> pd.DataFrame:
    return read_at1a('tests/sample_gravity.csv')


@pytest.fixture(scope='session')
def gpsdata() -> pd.DataFrame:
    return import_trajectory('tests/sample_trajectory.txt', timeformat='hms',
                             skiprows=1)
