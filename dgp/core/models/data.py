# -*- encoding: utf-8 -*-
from pathlib import Path
from typing import Optional

from core.oid import OID


class DataFile:
    __slots__ = '_uid', '_hdfpath', '_label', '_group', '_source_path', '_column_format'

    def __init__(self, hdfpath: str, label: str, group: str, source_path: Optional[Path] = None,
                 column_format=None, uid: Optional[str] = None):
        self._uid = OID(self, _uid=uid)
        self._hdfpath = hdfpath
        self._label = label
        self._group = group
        self._source_path = source_path
        self._column_format = column_format

    @property
    def uid(self) -> OID:
        return self._uid

    @property
    def group(self) -> str:
        return self._group

    def __str__(self):
        return "(%s) %s :: %s" % (self._group, self._label, self._hdfpath)


