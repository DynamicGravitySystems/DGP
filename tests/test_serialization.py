# -*- coding: utf-8 -*-
import json
import time
from datetime import datetime, date
from pathlib import Path
from pprint import pprint

import pandas as pd
import pytest

from dgp.core.models.data import DataFile
from dgp.core.models.flight import Flight
from dgp.core.models.project import AirborneProject, ProjectEncoder, ProjectDecoder, PROJECT_FILE_NAME


"""Test Project is created as a global fixture in conftest.py"""


def test_project_serialize(project: AirborneProject, tmpdir):
    _description = "Description for project that will be serialized."
    project.description = _description

    encoded = project.to_json(indent=4)
    decoded_dict = json.loads(encoded)

    assert project.name == decoded_dict['name']
    assert {'_type': 'Path', 'path': str(project.path.resolve())} == decoded_dict['path']
    for flight_obj in decoded_dict['flights']:
        assert '_type' in flight_obj and flight_obj['_type'] == 'Flight'

    _date = date.today()
    enc_date = json.dumps(_date, cls=ProjectEncoder)
    assert _date == json.loads(enc_date, cls=ProjectDecoder, klass=None)
    with pytest.raises(TypeError):
        json.dumps(pd.DataFrame([0, 1]), cls=ProjectEncoder)

    # Test serialize to file
    project.to_json(to_file=True)
    assert project.path.joinpath(PROJECT_FILE_NAME).exists()


def test_project_deserialize(project: AirborneProject):
    flt1 = project.flights[0]
    flt2 = project.flights[1]

    serialized = project.to_json(indent=4)
    time.sleep(0.20)  # Fuzz for modification date
    prj_deserialized = AirborneProject.from_json(serialized)
    re_serialized = prj_deserialized.to_json(indent=4)
    assert serialized == re_serialized

    assert project.create_date == prj_deserialized.create_date

    flt_names = [flt.name for flt in prj_deserialized.flights]
    assert flt1.name in flt_names
    assert flt2.name in flt_names

    f1_reconstructed = prj_deserialized.get_child(flt1.uid)
    assert flt1.uid in [flt.uid for flt in prj_deserialized.flights]
    assert 2 == len(prj_deserialized.flights)
    prj_deserialized.remove_child(f1_reconstructed.uid)
    assert 1 == len(prj_deserialized.flights)
    assert flt1.uid not in [flt.uid for flt in prj_deserialized.flights]
    assert f1_reconstructed.name == flt1.name
    assert f1_reconstructed.uid == flt1.uid

    assert flt2.uid in [flt.uid for flt in prj_deserialized.flights]


def test_parent_child_serialization():
    """Test that an object _parent reference is correctly serialized and deserialized
        i.e. when a child say FlightLine or DataFile is added to a flight, it should
        have a reference to its parent Flight.
        When de-serializing, check to see that this reference has been correctly assembled
    """
    prj = AirborneProject(name="Parent-Child-Test", path=Path('.'))
    flt = Flight('Flight-1')
    data1 = DataFile('gravity', datetime.now(), Path('./data1.dat'))

    # flt.add_child(data1)
    # assert flt == data1.parent

    prj.add_child(flt)
    assert flt in prj.flights

    encoded = prj.to_json(indent=2)
    # pprint(encoded)

    decoded = AirborneProject.from_json(encoded)

    assert 1 == len(decoded.flights)
    flt_ = decoded.flights[0]
