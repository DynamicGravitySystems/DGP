# -*- coding: utf-8 -*-
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication

from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.core.hdf5_manager import HDF5_NAME
from dgp.core.models.datafile import DataFile
from dgp.core.models.dataset import DataSegment, DataSet
from dgp.core.models.flight import Flight
from dgp.core.models.meter import Gravimeter
from dgp.core.models.project import AirborneProject
from dgp.core.oid import OID
from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.trajectory_ingestor import import_trajectory

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

"""Global pytest configuration file for DGP test suite.

This takes care of configuring a QApplication instance for executing tests 
against UI code which requires an event loop (signals etc).
If a handle to the QApplication is required, e.g. to use as the parent to a test 
object, the qt_app fixture can be used.

The sys.excepthook is also replaced to enable catching of some critical errors
raised within the Qt domain that would otherwise not be printed.

"""


def excepthook(type_, value, traceback_):
    """This allows IDE to properly display unhandled exceptions which are
    otherwise silently ignored as the application is terminated.
    Override default excepthook with
    >>> sys.excepthook = excepthook

    See Also
    --------

    http://pyqt.sourceforge.net/Docs/PyQt5/incompatibilities.html
    """
    traceback.print_exception(type_, value, traceback_)
    QtCore.qFatal('')


sys.excepthook = excepthook
APP = QApplication([])


def get_ts(offset=0):
    return datetime.now().timestamp() + offset


@pytest.fixture(scope='module')
def qt_app():
    return APP


@pytest.fixture()
def project_factory():
    def _factory(name, path, flights=2, dataset=True):
        base_dir = Path(path)
        prj = AirborneProject(name=name, path=base_dir.joinpath(''.join(name.split(' '))),
                              description=f"Description of {name}")
        prj.path.mkdir()

        flt1 = Flight("Flt1", sequence=0, duration=4)
        flt2 = Flight("Flt2", sequence=1, duration=6)

        mtr = Gravimeter.from_ini(Path('tests').joinpath('at1m.ini'), name="AT1A-X")

        grav1 = DataFile('gravity', datetime.now(), base_dir.joinpath('gravity1.dat'))
        traj1 = DataFile('trajectory', datetime.now(), base_dir.joinpath('gps1.dat'))
        seg1 = DataSegment(OID(), get_ts(0), get_ts(1500), 0, "seg1")
        seg2 = DataSegment(OID(), get_ts(1501), get_ts(3000), 1, "seg2")

        if dataset:
            dataset1 = DataSet(grav1, traj1, [seg1, seg2])
            flt1.datasets.append(dataset1)

        prj.add_child(mtr)
        prj.add_child(flt1)
        prj.add_child(flt2)
        return prj
    return _factory



@pytest.fixture()
def project(project_factory, tmpdir):
    """This fixture constructs a project model with a flight, gravimeter,
    DataSet (and its children - DataFile/DataSegment) for testing the serialization
    and de-serialization of a fleshed out project.
    """
    return project_factory("TestProject", tmpdir)


@pytest.fixture()
def prj_ctrl(project):
    return AirborneProjectController(project)


@pytest.fixture
def flt_ctrl(prj_ctrl: AirborneProjectController):
    return prj_ctrl.get_child(prj_ctrl.datamodel.flights[0].uid)


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
