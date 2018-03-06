# coding: utf-8

import pandas as pd


def named_series(*args, **kwargs):
    def wrapper(*args, **kwargs):
        return pd.Series(*args, **kwargs)
    return wrapper

