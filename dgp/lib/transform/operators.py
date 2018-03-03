# coding: utf-8

import pandas as pd
from functools import partial


def concat():
    return partial(pd.concat, join='outer', axis=1)
