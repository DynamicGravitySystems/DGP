# -*- coding: utf-8 -*-

from typing import Optional, Union
from uuid import uuid4

_registry = {}


def get_oid(oid: 'OID'):
    if oid.base_uuid in _registry:
        return _registry[oid.base_uuid]


class OID:
    """Object IDentifier - Replacing simple str UUID's that had been used.
        OID's hold a reference to the object it was created for.
    """
    def __init__(self, obj, tag: Optional[str]=None, _uid: str=None):
        if _uid is not None:
            assert len(_uid) == 32
        self._base_uuid = _uid or uuid4().hex
        self._group = obj.__class__.__name__[0:6].lower()
        self._uuid = '{}_{}'.format(self._group, self._base_uuid)
        self._tag = tag
        self._pointer = obj
        _registry[self._base_uuid] = self

    @property
    def tag(self):
        return self._tag

    @property
    def reference(self) -> object:
        return self._pointer

    @property
    def base_uuid(self):
        return self._base_uuid

    def __str__(self):
        return self._uuid

    def __repr__(self):
        return "<OID [%s] - %s pointer: %s>" % (self._tag, self._uuid, self._pointer.__class__.__name__)

    def __eq__(self, other: Union['OID', str]) -> bool:
        if isinstance(other, str):
            return other == self._base_uuid or other == self._uuid
        try:
            return self._base_uuid == other.base_uuid
        except AttributeError:
            return False

    def __hash__(self):
        return hash(self.base_uuid)

    def __del__(self):
        # print("Deleting OID from registry: " + self._base_uuid)
        try:
            del _registry[self._base_uuid]
        except KeyError:
            pass
        else:
            pass
            # print("Key deleted sucessfully")
