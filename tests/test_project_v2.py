# -*- coding: utf-8 -*-

"""
Unit tests for new Project/Flight data classes, including JSON
serialization/de-serialization
"""
import json
from pathlib import Path
from pprint import pprint

import pytest
from dgp.core import flight, project


@pytest.fixture()
def make_flight():
    def _factory(name):
        return flight.Flight(name)
    return _factory


@pytest.fixture()
def make_line():
    seq = 0

    def _factory(start, stop):
        nonlocal seq
        seq += 1
        return flight.FlightLine(start, stop, seq)
    return _factory


def test_flight_actions(make_flight, make_line):
    flt = flight.Flight('test_flight')
    assert 'test_flight' == flt.name

    f1 = make_flight('Flight-1')  # type: flight.Flight
    f2 = make_flight('Flight-2')  # type: flight.Flight

    assert 'Flight-1' == f1.name
    assert 'Flight-2' == f2.name

    assert not f1.uid == f2.uid

    line1 = make_line(0, 10)  # type: flight.FlightLine
    line2 = make_line(11, 21)  # type: flight.FlightLine

    assert not line1.sequence == line2.sequence

    assert 0 == f1.flight_line_count()
    assert 0 == f1.data_file_count()

    f1.add_flight_line(line1)
    assert 1 == f1.flight_line_count()

    with pytest.raises(ValueError):
        f1.add_flight_line('not a flight line')

    assert line1 in f1.flight_lines

    f1.remove_flight_line(line1.uid)
    assert line1 not in f1.flight_lines

    f1.add_flight_line(line1)
    f1.add_flight_line(line2)

    assert line1 in f1.flight_lines
    assert line2 in f1.flight_lines
    assert 2 == f1.flight_line_count()

    assert '<Flight Flight-1 :: %s>' % f1.uid == repr(f1)


def test_project_actions():
    pass


def test_project_attr(make_flight):
    prj_path = Path('./project-1')
    prj = project.AirborneProject(name="Project-1", path=prj_path,
                                  description="Test Project 1")
    assert "Project-1" == prj.name
    assert prj_path == prj.path
    assert "Test Project 1" == prj.description

    prj.set_attr('tie_value', 1234)
    assert 1234 == prj.tie_value
    assert 1234 == prj['tie_value']
    assert 1234 == prj.get_attr('tie_value')

    prj.set_attr('_my_private_val', 2345)
    assert 2345 == prj._my_private_val
    assert 2345 == prj['_my_private_val']
    assert 2345 == prj.get_attr('_my_private_val')

    flt1 = make_flight('flight-1')
    prj.add_flight(flt1)
    # assert flt1.parent == prj.uid


def test_project_serialize(make_flight, make_line):
    prj_path = Path('./prj-1')
    prj = project.AirborneProject(name="Project-1", path=prj_path,
                                  description="Test Project Serialization")
    f1 = make_flight('flt1')  # type: flight.Flight
    line1 = make_line(0, 10)  # type: # flight.FlightLine
    data1 = flight.DataFile('/%s' % f1.uid.base_uuid, 'df1', 'gravity')
    f1.add_flight_line(line1)
    f1.add_data_file(data1)
    prj.add_flight(f1)

    prj.set_attr('start_tie_value', 1234.90)
    prj.set_attr('end_tie_value', 987.123)

    encoded = prj.to_json(indent=4)

    decoded_dict = json.loads(encoded)

    pprint(decoded_dict)


def test_project_deserialize(make_flight, make_line):
    prj = project.AirborneProject(name="SerializeTest", path=Path('./prj1'),
                                  description="Test DeSerialize")

    f1 = make_flight("Flt1")
    f2 = make_flight("Flt2")
    line1 = make_line(0, 10)
    line2 = make_line(11, 20)
    f1.add_flight_line(line1)
    f1.add_flight_line(line2)

    prj.add_flight(f1)
    prj.add_flight(f2)

    serialized = prj.to_json(indent=4)

    prj_deserialized = project.AirborneProject.from_json(serialized)
    flt_names = [flt.name for flt in prj_deserialized.flights]

    assert prj.creation_time == prj_deserialized.creation_time

    assert "Flt1" in flt_names
    assert "Flt2" in flt_names

    f1_reconstructed = prj_deserialized.flight(f1.uid)
    assert f1_reconstructed.name == f1.name


