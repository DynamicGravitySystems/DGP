# -*- coding: utf-8 -*-

import pytest

from dgp.core.oid import OID


def test_oid_equivalence():
    oid1 = OID('flt')
    oid2 = OID('flt')

    assert not oid1 == oid2

    oid2_clone = OID(tag="test", base_uuid=oid2.base_uuid)
    assert oid2 == oid2_clone
    assert "oid" == oid2_clone.group
    assert "test" == oid2_clone.tag

    assert str(oid2.base_uuid) == oid2_clone

    assert not oid2 == dict(expect="Failure")
