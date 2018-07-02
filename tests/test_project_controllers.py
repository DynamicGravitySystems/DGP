# -*- coding: utf-8 -*-
import random
from datetime import datetime
from pathlib import Path

import pytest
from PyQt5.QtCore import Qt, QAbstractItemModel

from .context import APP
from dgp.core.controllers.datafile_controller import DataFileController
from dgp.core.models.data import DataFile
from dgp.core.controllers.flight_controller import FlightController
from dgp.core.models.flight import Flight, FlightLine


@pytest.fixture
def flight_ctrl():
    pass


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


def test_datafile_controller():
    flight = Flight('test_flightline_controller')
    fl_controller = FlightController(flight)
    datafile = DataFile('gravity', datetime(2018, 6, 15),
                        source_path=Path('c:\\data\\gravity.dat'))
    fl_controller.add_child(datafile)

    assert datafile in flight.data_files

    assert isinstance(fl_controller._data_files.child(0), DataFileController)


def test_gravimeter_controller():
    pass


def test_flight_controller(make_line):
    flight = Flight('Test-Flt-1')
    fc = FlightController(flight)

    assert flight.uid == fc.uid
    assert flight.name == fc.data(Qt.DisplayRole)

    line1 = make_line()
    line2 = make_line()
    line3 = make_line()

    data1 = DataFile('gravity', datetime(2018, 5, 15), Path('./data1.dat'))
    data2 = DataFile('gravity', datetime(2018, 5, 25), Path('./data2.dat'))

    assert fc.add_child(line1)
    assert fc.add_child(line2)
    assert fc.add_child(data1)
    assert fc.add_child(data2)

    assert line1 in flight.flight_lines
    assert line2 in flight.flight_lines

    assert data1 in flight.data_files
    assert data2 in flight.data_files

    model = fc.lines_model
    assert isinstance(model, QAbstractItemModel)
    assert 2 == model.rowCount()

    lines = [line1, line2]
    for i in range(model.rowCount()):
        index = model.index(i, 0)
        child = model.data(index, Qt.UserRole)
        assert lines[i] == child

    with pytest.raises(ValueError):
        fc.add_child({1: "invalid child"})

    fc.add_child(line3)


def test_airborne_project_controller():
    pass
