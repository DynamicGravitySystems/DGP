# -*- coding: utf-8 -*-

"""
New pure data class for Meter configurations
"""
from typing import Optional

from core.oid import OID


class Gravimeter:
    def __init__(self, uid: Optional[str]=None, **kwargs):
        self._uid = OID(self, _uid=uid)
        self._type = "AT1A"
        self._attributes = {}

    @property
    def uid(self) -> OID:
        return self._uid

    @classmethod
    def from_dict(cls, map):
        pass
