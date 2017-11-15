# coding: utf-8

import uuid
import numpy as np


def interp_nans(y):
    nans = np.isnan(y)
    x = lambda z: z.nonzero()[0]
    y[nans] = np.interp(x(nans), x(~nans), y[~nans])
    return y


def gen_uuid(prefix: str=''):
    """
    Generate a UUID4 String with optional prefix replacing the first len(prefix) characters of the
    UUID.
    Parameters
    ----------
    prefix : [str]
        Optional string prefix to be prepended to the generated UUID

    Returns
    -------
    str:
        UUID String of length 32
    """
    base_uuid = uuid.uuid4().hex
    return '{prefix}{uuid}'.format(prefix=prefix, uuid=base_uuid[len(prefix):])

def dedup_dict(d):
    t = [(k, d[k]) for k in d]
    t.sort()
    res = {}

    for key, val in t:
        if val in res.values():
            continue
        res[key] = val

    return res
