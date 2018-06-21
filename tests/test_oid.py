# -*- coding: utf-8 -*-

import pytest

from dgp.core.oid import OID


def test_oid_equivalence():
    oid1 = OID('flt')
    oid2 = OID('flt')

    assert not oid1 == oid2
