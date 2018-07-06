# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Optional, Union

from dgp.core.models.data import DataFile
from dgp.core.models.meter import Gravimeter
from dgp.core.oid import OID


class FlightLine:
    __slots__ = ('uid', 'parent', 'label', 'sequence',  '_start', '_stop')

    def __init__(self, start: float, stop: float, sequence: int,
                 label: Optional[str] = "", uid: Optional[OID] = None):
        self.uid = uid or OID(self)
        self.uid.set_pointer(self)
        self.parent = None
        self.label = label
        self.sequence = sequence
        self._start = start
        self._stop = stop

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

    def set_parent(self, parent):
        self.parent = parent

    def __str__(self):
        return 'Line {} {:%H:%M} -> {:%H:%M}'.format(self.sequence, self.start, self.stop)


class Flight:
    """
    Version 2 Flight Class - Designed to be de-coupled from the view implementation
    Define a Flight class used to record and associate data with an entire
    survey flight (takeoff -> landing)
    """
    __slots__ = ('uid', 'name', '_flight_lines', '_data_files', '_meter', 'date',
                 'notes', 'sequence', 'duration', 'parent')

    def __init__(self, name: str, date: Optional[datetime] = None, notes: Optional[str] = None,
                 sequence: int = 0, duration: int = 0, meter: str = None,
                 uid: Optional[OID] = None, **kwargs):
        self.parent = None
        self.uid = uid or OID(self, name)
        self.uid.set_pointer(self)
        self.name = name
        self.date = date or datetime.today()
        self.notes = notes
        self.sequence = sequence
        self.duration = duration

        self._flight_lines = kwargs.get('flight_lines', [])  # type: List[FlightLine]
        self._data_files = kwargs.get('data_files', [])  # type: List[DataFile]
        self._meter = meter

    @property
    def data_files(self) -> List[DataFile]:
        return self._data_files

    @property
    def flight_lines(self) -> List[FlightLine]:
        return self._flight_lines

    def add_child(self, child: Union[FlightLine, DataFile, Gravimeter]) -> None:
        # TODO: Is add/remove child necesarry or useful, just allow direct access to the underlying lists?
        if child is None:
            return
        if isinstance(child, FlightLine):
            self._flight_lines.append(child)
        elif isinstance(child, DataFile):
            self._data_files.append(child)
        elif isinstance(child, Gravimeter):  # pragma: no cover
            # TODO: Implement this properly
            self._meter = child.uid.base_uuid
        else:
            raise TypeError("Invalid child type supplied: <%s>" % str(type(child)))
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
        self.parent = parent

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return '<Flight %s :: %s>' % (self.name, self.uid)
