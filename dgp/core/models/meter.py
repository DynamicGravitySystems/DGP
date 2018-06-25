# -*- coding: utf-8 -*-

"""
New pure data class for Meter configurations
"""
from typing import Optional

from ..oid import OID


class Gravimeter:
    def __init__(self, name: str, uid: Optional[str]=None, **kwargs):
        self._uid = OID(self, _uid=uid)
        self._type = "AT1A"
        self._name = name
        self._attributes = kwargs.get('attributes', {})

    @property
    def uid(self) -> OID:
        return self._uid

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        # ToDo: Regex validation?
        self._name = value
