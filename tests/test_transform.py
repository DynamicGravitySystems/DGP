# coding: utf-8

import os
import unittest
import numpy as np
import pandas as pd

from .context import  dgp
from dgp.lib.transform import TransformChain, DataWrapper

class TestTransform(unittest.TestCase):
    def test_basic_transform_chain_ops(self):
        df = pd.DataFrame({'A': range(11), 'B': range(11)})

        tc = TransformChain()

        def transform1(df):
            df['A'] = df['A'] + 3.
            return df

        def transform2(df):
            df['A'] = df['A'] + df['B']
            return df

        def transform3(df):
            df = (df + df.shift(1)).dropna()
            return df

        tc.add_transform(transform1)
        tc.add_transform(transform2)
        tc.add_transform(transform3)

        self.assertTrue(len(tc) == 3)

        new_df = tc.apply(df)

        df['A'] = df['A'] + 3.
        df['A'] = df['A'] + df['B']
        df = (df + df.shift(1)).dropna()

        self.assertTrue(new_df.equals(df))
