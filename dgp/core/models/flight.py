# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Optional, Union

from dgp.core.models.data import DataFile
from dgp.core.models.meter import Gravimeter
from dgp.core.oid import OID


class FlightLine:
    __slots__ = ('_uid', '_label', '_start', '_stop', '_sequence', '_parent')

    def __init__(self, start: float, stop: float, sequence: int,
                 label: Optional[str] = "", uid: Optional[OID] = None):
        self._parent = None
        self._uid = uid or OID(self)
        self._uid.set_pointer(self)
        self._start = start
        self._stop = stop
        self._sequence = sequence
        self._label = label

    @property
    def uid(self) -> OID:
        return self._uid

    @property
    def start(self) -> datetime:
        return datetime.fromtimestamp(self._start)

    @start.setter
    def start(self, value: float) -> None:
        self._start = value

    @property
    def stop(self) -> datetime:
        return datetime.fromtimestamp(self._stop)

    @stop.setter
    def stop(self, value: float) -> None:
        self._stop = value

    @property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, value: str) -> None:
        self._label = value

    @property
    def sequence(self) -> int:
        return self._sequence

    def set_parent(self, parent):
        self._parent = parent

    def __str__(self):
        return 'Line {} {:%H:%M} -> {:%H:%M}'.format(self.sequence, self.start, self.stop)


class Flight:
    """
    Version 2 Flight Class - Designed to be de-coupled from the view implementation
    Define a Flight class used to record and associate data with an entire
    survey flight (takeoff -> landing)
    """
    __slots__ = ('_uid', '_name', '_flight_lines', '_data_files', '_meter', '_date',
                 '_notes', '_sequence', '_duration', '_parent')

    def __init__(self, name: str, date: Optional[datetime] = None, notes: Optional[str] = None,
                 sequence: int = 0, duration: int = 0, meter: str = None,
                 uid: Optional[OID] = None, **kwargs):
        self._parent = None
        self._uid = uid or OID(self, name)
        self._uid.set_pointer(self)
        self._name = name
        self._date = date
        self._notes = notes
        self._sequence = sequence
        self._duration = duration

        self._flight_lines = kwargs.get('flight_lines', [])  # type: List[FlightLine]
        self._data_files = kwargs.get('data_files', [])  # type: List[DataFile]
        self._meter: str = meter

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def date(self) -> datetime:
        return self._date

    @date.setter
    def date(self, value: datetime) -> None:
        self._date = value

    @property
    def notes(self) -> str:
        return self._notes

    @notes.setter
    def notes(self, value: str) -> None:
        self._notes = value

    @property
    def sequence(self) -> int:
        return self._sequence

    @sequence.setter
    def sequence(self, value: int) -> None:
        self._sequence = value

    @property
    def duration(self) -> int:
        return self._duration

    @duration.setter
    def duration(self, value: int) -> None:
        self._duration = value

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
        if child is None:
            return
        if isinstance(child, FlightLine):
            self._flight_lines.append(child)
        elif isinstance(child, DataFile):
            self._data_files.append(child)
        elif isinstance(child, Gravimeter):
            self._meter = child.uid.base_uuid
        else:
            raise ValueError("Invalid child type supplied: <%s>" % str(type(child)))
        child.set_parent(self)

    def remove_child(self, child: Union[FlightLine, DataFile, OID]) -> bool:
        if isinstance(child, OID):
            child = child.reference
        if isinstance(child, FlightLine):
            child.set_parent(None)
            self._flight_lines.remove(child)
        elif isinstance(child, DataFile):
            child.set_parent(None)
            self._data_files.remove(child)
        else:
            return False
        return True

    def set_parent(self, parent):
        self._parent = parent

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return '<Flight %s :: %s>' % (self.name, self.uid)
