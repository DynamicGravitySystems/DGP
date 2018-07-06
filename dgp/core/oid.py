# -*- coding: utf-8 -*-

from typing import Optional, Union, Any
from uuid import uuid4


class OID:
    """Object IDentifier

    Designed as a replacement for the simple string UUID's used previously.
    OID's hold a reference to the object it was created for.
    OID's can also contain simple meta-data such as a tag for the object it
    references.
    """

    def __init__(self, obj: Optional[Any] = None, tag: Optional[str] = None, base_uuid: str = None):
        if base_uuid is not None and isinstance(base_uuid, str):
            assert len(base_uuid) == 32
        self._base_uuid = base_uuid or uuid4().hex
        self._tag = tag
        self._pointer = obj

    def set_pointer(self, obj):
        self._pointer = obj

    @property
    def base_uuid(self):
        return self._base_uuid

    @property
    def uuid(self):
        return '%s_%s' % (self.group, self._base_uuid)

    @property
    def reference(self) -> object:
        return self._pointer

    @property
    def group(self) -> str:
        if self._pointer is not None:
            return self._pointer.__class__.__name__.lower()
        return "oid"

    @property
    def tag(self):
        return self._tag

    def __str__(self):
        return self.uuid

    def __repr__(self):
        return "<OID [%s] - %s pointer: %s>" % (self._tag, self.uuid, self.group)

    def __eq__(self, other: Union['OID', str]) -> bool:
        if isinstance(other, str):
            return other == self._base_uuid or other == self.uuid
        try:
            return self._base_uuid == other.base_uuid
        except AttributeError:
            return False

    def __hash__(self):
        return hash(self.base_uuid)
