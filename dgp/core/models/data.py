# -*- encoding: utf-8 -*-
from datetime import datetime
from pathlib import Path
from typing import Optional

from dgp.core.oid import OID


class DataFile:
    __slots__ = ('parent', 'uid', 'date', 'name', 'group', 'source_path',
                 'column_format')

    def __init__(self, group: str, date: datetime, source_path: Path,
                 name: Optional[str] = None, column_format=None,
                 uid: Optional[OID] = None, parent=None):
        self.parent = parent
        self.uid = uid or OID(self)
        self.uid.set_pointer(self)
        self.group = group.lower()
        self.date = date
        self.source_path = Path(source_path)
        self.name = name or self.source_path.name
        self.column_format = column_format

    @property
    def label(self) -> str:
        return "[%s] %s" % (self.group, self.name)

    @property
    def hdfpath(self) -> str:
        """Construct the HDF5 Node path where the DataFile is stored

        Notes
        -----
        An underscore (_) is prepended to the parent and uid ID's to suppress the NaturalNameWarning
        generated if the UID begins with a number (invalid Python identifier).
        """
        return '/_{parent}/{group}/_{uid}'.format(parent=self.parent.uid.base_uuid,
                                                  group=self.group, uid=self.uid.base_uuid)

    def set_parent(self, parent):
        self.parent = parent

    def __str__(self):
        return "(%s) :: %s" % (self.group, self.hdfpath)

    def __hash__(self):
        return hash(self.uid)
