# -*- coding: utf-8 -*-

"""
Unit tests for new Project/Flight data classes, including JSON
serialization/de-serialization
"""
import json
import time
import random
from datetime import datetime
from typing import Tuple
from uuid import uuid4
from pathlib import Path
from pprint import pprint

import pytest

from dgp.core.models.data import DataFile
from dgp.core.models import project, flight
from dgp.core.models.meter import Gravimeter


@pytest.fixture()
def make_flight():
    def _factory() -> Tuple[str, flight.Flight]:
        name = str(uuid4().hex)[:12]
        return name, flight.Flight(name)
    return _factory


@pytest.fixture()
def make_line():
    seq = 0

    def _factory():
        nonlocal seq
        seq += 1
        return flight.FlightLine(datetime.now().timestamp(),
                                 datetime.now().timestamp() + round(random.random() * 1000),
                                 seq)
    return _factory


def test_flight_actions(make_flight, make_line):
    flt = flight.Flight('test_flight')
    assert 'test_flight' == flt.name

    f1_name, f1 = make_flight()  # type: flight.Flight
    f2_name, f2 = make_flight()  # type: flight.Flight

    assert f1_name == f1.name
    assert f2_name == f2.name

    assert not f1.uid == f2.uid

    line1 = make_line()  # type: flight.FlightLine
    line2 = make_line()  # type: flight.FlightLine

    assert not line1.sequence == line2.sequence

    assert 0 == len(f1.flight_lines)
    assert 0 == len(f2.flight_lines)

    f1.add_child(line1)
    assert 1 == len(f1.flight_lines)

    with pytest.raises(ValueError):
        f1.add_child('not a flight line')

    assert line1 in f1.flight_lines

    f1.remove_child(line1.uid)
    assert line1 not in f1.flight_lines

    f1.add_child(line1)
    f1.add_child(line2)

    assert line1 in f1.flight_lines
    assert line2 in f1.flight_lines
    assert 2 == len(f1.flight_lines)

    assert '<Flight %s :: %s>' % (f1_name, f1.uid) == repr(f1)


def test_project_attr():
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


def test_project_get_child(make_flight):
    prj = project.AirborneProject(name="Project-2", path=Path('.'))
    f1_name, f1 = make_flight()
    f2_name, f2 = make_flight()
    f3_name, f3 = make_flight()
    prj.add_child(f1)
    prj.add_child(f2)
    prj.add_child(f3)

    assert f1 == prj.get_child(f1.uid)
    assert f3 == prj.get_child(f3.uid)
    assert not f2 == prj.get_child(f1.uid)


def test_project_remove_child(make_flight):
    prj = project.AirborneProject(name="Project-3", path=Path('.'))
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


def test_project_serialize(make_flight, make_line):
    prj_path = Path('./prj-1')
    prj = project.AirborneProject(name="Project-3", path=prj_path,
                                  description="Test Project Serialization")
    f1_name, f1 = make_flight()  # type: flight.Flight
    line1 = make_line()  # type: # flight.FlightLine
    data1 = flight.DataFile('gravity', datetime.today(), Path('./fake_file.dat'))
    f1.add_child(line1)
    f1.add_child(data1)
    prj.add_child(f1)

    prj.set_attr('start_tie_value', 1234.90)
    prj.set_attr('end_tie_value', 987.123)

    encoded = prj.to_json(indent=4)

    decoded_dict = json.loads(encoded)
    # pprint(decoded_dict)

    assert 'Project-3' == decoded_dict['name']
    assert {'_type': 'Path', 'path': 'prj-1'} == decoded_dict['path']
    assert 'start_tie_value' in decoded_dict['attributes']
    assert 1234.90 == decoded_dict['attributes']['start_tie_value']
    assert 'end_tie_value' in decoded_dict['attributes']
    assert 987.123 == decoded_dict['attributes']['end_tie_value']
    for flight_dict in decoded_dict['flights']:
        assert '_type' in flight_dict and flight_dict['_type'] == 'Flight'


def test_project_deserialize(make_flight, make_line):
    attrs = {
        'attr1': 12345,
        'attr2': 192.201,
        'attr3': False,
        'attr4': "Notes on project"
    }
    prj = project.AirborneProject(name="SerializeTest", path=Path('./prj1'),
                                  description="Test DeSerialize")

    for key, value in attrs.items():
        prj.set_attr(key, value)

    assert attrs == prj._attributes

    f1_name, f1 = make_flight()  # type: flight.Flight
    f2_name, f2 = make_flight()
    line1 = make_line()  # type: flight.FlightLine
    line2 = make_line()
    data1 = DataFile('gravity', datetime.today(), Path('./data1.dat'))
    f1.add_child(line1)
    f1.add_child(line2)
    f1.add_child(data1)

    prj.add_child(f1)
    prj.add_child(f2)

    mtr = Gravimeter('AT1M-X')
    prj.add_child(mtr)

    serialized = prj.to_json(indent=4)
    time.sleep(0.20)  # Fuzz for modification date
    prj_deserialized = project.AirborneProject.from_json(serialized)
    re_serialized = prj_deserialized.to_json(indent=4)
    assert serialized == re_serialized

    assert attrs == prj_deserialized._attributes
    assert prj.creation_time == prj_deserialized.creation_time

    flt_names = [flt.name for flt in prj_deserialized.flights]
    assert f1_name in flt_names
    assert f2_name in flt_names

    f1_reconstructed = prj_deserialized.get_child(f1.uid)
    assert f1.uid in [flt.uid for flt in prj_deserialized.flights]
    assert 2 == len(prj_deserialized.flights)
    prj_deserialized.remove_child(f1_reconstructed.uid)
    assert 1 == len(prj_deserialized.flights)
    assert f1.uid not in [flt.uid for flt in prj_deserialized.flights]
    assert f1_reconstructed.name == f1.name
    assert f1_reconstructed.uid == f1.uid

    assert f2.uid in [flt.uid for flt in prj_deserialized.flights]

    assert line1.uid in [line.uid for line in f1_reconstructed.flight_lines]
    assert line2.uid in [line.uid for line in f1_reconstructed.flight_lines]


def test_parent_child_serialization():
    """Test that an object _parent reference is correctly serialized and deserialized
        i.e. when a child say FlightLine or DataFile is added to a flight, it should
        have a reference to its parent Flight.
        When de-serializing, check to see that this reference has been correctly assembled
    """
    prj = project.AirborneProject(name="Parent-Child-Test", path=Path('.'))
    flt = flight.Flight('Flight-1')
    data1 = DataFile('gravity', datetime.now(), Path('./data1.dat'))

    flt.add_child(data1)
    assert flt == data1._parent

    prj.add_child(flt)
    assert flt in prj.flights

    encoded = prj.to_json(indent=2)
    # pprint(encoded)

    decoded = project.AirborneProject.from_json(encoded)

    assert 1 == len(decoded.flights)
    flt_ = decoded.flights[0]
    assert 1 == len(flt_.data_files)
    data_ = flt_.data_files[0]
    assert flt_ == data_._parent


