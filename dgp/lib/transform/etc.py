# coding: utf-8

import pandas as pd
from functools import partial


def named_series(name):
    return partial(pd.Series, name=name)

