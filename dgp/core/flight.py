# -*- coding: utf-8 -*-
from typing import List, Optional, Any, Dict

from dgp.lib.datastore import store
from core.oid import OID



class FlightLine:
    def __init__(self, start, stop, sequence: int, uid: Optional[str]=None,
                 **kwargs):
        self._uid = OID(self, _uid=uid)

        self._start = start
        self._stop = stop
        self._sequence = sequence

    @property
    def uid(self) -> OID:
        return self._uid

    @property
    def start(self) -> int:
        return self._start

    @start.setter
    def start(self, value: int) -> None:
        self._start = value

    @property
    def stop(self) -> int:
        return self._stop

    @stop.setter
    def stop(self, value: int) -> None:
        self._stop = value

    @property
    def sequence(self) -> int:
        return self._sequence


class DataFile:
    def __init__(self, path: str, label: str, group: str, uid: Optional[str]=None, **kwargs):
        self._uid = OID(self, _uid=uid)
        self._path = path
        self._label = label
        self._group = group

    def load(self):
        try:
            pass
            # store.load_data()
        except AttributeError:
            return None
        return None


class Flight:
    """
    Version 2 Flight Class - Designed to be de-coupled from the view implementation
    Define a Flight class used to record and associate data with an entire
    survey flight (takeoff -> landing)
    This class is iterable, yielding the flightlines named tuple objects from
    its lines dictionary
    """

    def __init__(self, name: str, uid: Optional[str]=None, **kwargs):
        self._uid = OID(self, tag=name, _uid=uid)
        self._name = name

        self._flight_lines = []  # type: List[FlightLine]
        self._data_files = []  # type: List[DataFile]
        self._meters = []  # type: List[str]

    @property
    def name(self) -> str:
        return self._name

    @property
    def uid(self) -> OID:
        return self._uid

    @property
    def data_files(self):
        return self._data_files

    def add_data_file(self, file: DataFile) -> None:
        """Add a data file (via its HDF5 file path)"""
        self._data_files.append(file)

    def remove_data_file(self, path: str) -> bool:
        try:
            self._data_files.remove(path)
        except ValueError:
            return False
        else:
            return True

    def data_file_count(self):
        return len(self._data_files)

    @property
    def flight_lines(self):
        return self._flight_lines

    def add_flight_line(self, line: FlightLine):
        if not isinstance(line, FlightLine):
            raise ValueError("Invalid input type, expected: %s" % str(type(FlightLine)))
        # line.parent = self.uid
        self._flight_lines.append(line)

    def remove_flight_line(self, uid):
        for i, line in enumerate(self._flight_lines):
            if line.uid == uid:
                idx = i
                break
        else:
            return False

        return self._flight_lines.pop(idx)

    def flight_line_count(self):
        return len(self._flight_lines)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Flight %s :: %s>' % (self.name, self.uid)

    @classmethod
    def from_dict(cls, mapping: Dict[str, Any]):
        assert mapping.pop('_type') == cls.__name__
        flt_lines = mapping.pop('_flight_lines')
        flt_meters = mapping.pop('_meters')
        flt_data = mapping.pop('_data_files')

        params = {}
        for key, value in mapping.items():
            param_key = key[1:] if key.startswith('_') else key
            params[param_key] = value

        klass = cls(**params)

        for line in flt_lines:
            line.pop('_type')
            flt_line = FlightLine(**{key[1:]: value for key, value in line.items()})
            klass.add_flight_line(flt_line)

        for file in flt_data:
            data_file = DataFile(**file)
            klass.add_data_file(data_file)

        for meter in flt_meters:
            # TODO: Implement
            pass

        return klass
