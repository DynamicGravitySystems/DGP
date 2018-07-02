# -*- encoding: utf-8 -*-
from datetime import datetime
from pathlib import Path
from typing import Optional

from dgp.core.oid import OID


class DataFile:
    __slots__ = ('_parent', '_uid', '_date', '_name', '_group', '_source_path',
                 '_column_format')

    def __init__(self, group: str, date: datetime, source_path: Path,
                 name: Optional[str] = None, column_format=None,
                 uid: Optional[OID] = None, parent=None):
        self._parent = parent
        self._uid = uid or OID(self)
        self._uid.set_pointer(self)
        self._group = group.lower()
        self._date = date
        self._source_path = Path(source_path)
        self._name = name or self._source_path.name
        self._column_format = column_format

    @property
    def uid(self) -> OID:
        return self._uid

    @property
    def name(self) -> str:
        """Return the file name of the source data file"""
        return self._name

    @property
    def label(self) -> str:
        return "[%s] %s" % (self.group, self.name)

    @property
    def group(self) -> str:
        return self._group

    @property
    def hdfpath(self) -> str:
        """Construct the HDF5 Node path where the DataFile is stored

        Notes
        -----
        An underscore (_) is prepended to the parent and uid ID's to suppress the NaturalNameWarning
        generated if the UID begins with a number (invalid Python identifier).
        """
        return '/_{parent}/{group}/_{uid}'.format(parent=self._parent.uid.base_uuid,
                                                  group=self._group, uid=self._uid.base_uuid)

    @property
    def source_path(self) -> Path:
        if self._source_path is not None:
            return Path(self._source_path)

    def set_parent(self, parent):
        self._parent = parent

    def __str__(self):
        return "(%s) :: %s" % (self._group, self.hdfpath)

    def __hash__(self):
        return hash(self._uid)
