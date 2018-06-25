# -*- coding: utf-8 -*-
from pathlib import Path
from typing import List, Optional, Any, Dict, Union

from .meter import Gravimeter
from ..oid import OID


class FlightLine:
    __slots__ = '_uid', '_start', '_stop', '_sequence'

    def __init__(self, start: float, stop: float, sequence: int,
                 uid: Optional[str]=None):
        self._uid = OID(self, _uid=uid)

        self._start = start
        self._stop = stop
        self._sequence = sequence

    @property
    def uid(self) -> OID:
        return self._uid

    @property
    def start(self) -> float:
        return self._start

    @start.setter
    def start(self, value: float) -> None:
        self._start = value

    @property
    def stop(self) -> float:
        return self._stop

    @stop.setter
    def stop(self, value: float) -> None:
        self._stop = value

    @property
    def sequence(self) -> int:
        return self._sequence

    def __str__(self):
        return "Line %d :: %.4f (start)  %.4f (end)" % (self.sequence, self.start, self.stop)


class DataFile:
    __slots__ = '_uid', '_path', '_label', '_group', '_source_path', '_column_format'

    def __init__(self, hdfpath: str, label: str, group: str, source_path: Optional[Path]=None,
                 uid: Optional[str]=None, **kwargs):
        self._uid = OID(self, _uid=uid)
        self._path = hdfpath
        self._label = label
        self._group = group
        self._source_path = source_path
        self._column_format = None

    def load(self):
        try:
            pass
            # store.load_data()
        except AttributeError:
            return None
        return None

    @property
    def uid(self) -> OID:
        return self._uid

    def __str__(self):
        return "(%s) %s :: %s" % (self._group, self._label, self._path)


class Flight:
    """
    Version 2 Flight Class - Designed to be de-coupled from the view implementation
    Define a Flight class used to record and associate data with an entire
    survey flight (takeoff -> landing)
    This class is iterable, yielding the flightlines named tuple objects from
    its lines dictionary
    """
    __slots__ = '_uid', '_name', '_flight_lines', '_data_files', '_meters'

    def __init__(self, name: str, uid: Optional[str]=None, **kwargs):
        self._uid = OID(self, tag=name, _uid=uid)
        self._name = name

        self._flight_lines = kwargs.get('flight_lines', [])  # type: List[FlightLine]
        self._data_files = kwargs.get('data_files', [])  # type: List[DataFile]
        self._meters = kwargs.get('meters', [])  # type: List[OID]

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def uid(self) -> OID:
        return self._uid

    @property
    def data_files(self) -> List[DataFile]:
        return self._data_files

    @property
    def flight_lines(self) -> List[FlightLine]:
        return self._flight_lines

    def add_child(self, child: Union[FlightLine, DataFile, Gravimeter]) -> None:
        if isinstance(child, FlightLine):
            self._flight_lines.append(child)
        elif isinstance(child, DataFile):
            self._data_files.append(child)
        elif isinstance(child, Gravimeter):
            raise NotImplementedError("Meter Config Children not yet implemented")
        else:
            raise ValueError("Invalid child type supplied: <%s>" % str(type(child)))

    def remove_child(self, child: Union[FlightLine, DataFile, OID]) -> bool:
        if isinstance(child, OID):
            child = child.reference

        if isinstance(child, FlightLine):
            self._flight_lines.remove(child)
        elif isinstance(child, DataFile):
            self._data_files.remove(child)
        else:
            return False
        return True

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return '<Flight %s :: %s>' % (self.name, self.uid)

    # @classmethod
    # def from_dict(cls, mapping: Dict[str, Any]) -> 'Flight':
    #     # assert mapping.pop('_type') == cls.__name__
    #     flt_lines = mapping.pop('_flight_lines')
    #     flt_meters = mapping.pop('_meters')
    #     flt_data = mapping.pop('_data_files')
    #
    #     params = {}
    #     for key, value in mapping.items():
    #         param_key = key[1:] if key.startswith('_') else key
    #         params[param_key] = value
    #
    #     klass = cls(**params)
    #     for line in flt_lines:
    #         # assert 'FlightLine' == line.pop('_type')
    #         flt_line = FlightLine(**{key[1:]: value for key, value in line.items()})
    #         klass.add_child(flt_line)
    #
    #     for file in flt_data:
    #         data_file = DataFile(**file)
    #         klass.add_child(data_file)
    #
    #     for meter in flt_meters:
    #         # Should meters in a flight just be a UID reference to global meter configs?
    #         meter_cfg = Gravimeter(**meter)
    #         klass.add_child(meter_cfg)
    #
    #     return klass
