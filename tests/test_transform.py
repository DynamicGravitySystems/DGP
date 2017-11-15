# coding: utf-8

import os
import unittest
import numpy as np
import pandas as pd
from copy import deepcopy

from .context import  dgp
from dgp.lib.transform import TransformChain, DataWrapper

from copy import deepcopy

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

        tc.addtransform(transform1)
        tc.addtransform(transform2)
        tc.addtransform(transform3)

        self.assertTrue(len(tc) == 3)

        new_df_A = tc.apply(df)

        df_A = deepcopy(df)
        df_A['A'] = df_A['A'] + 3.
        df_A['A'] = df_A['A'] + df_A['B']
        df_A = (df_A + df_A.shift(1)).dropna()

        self.assertTrue(new_df_A.equals(df_A))

        # test reordering
        reordering = {tc[2]: 0, tc[0]: 2}
        reordered_uids = [tc.ordering[-1], tc.ordering[1], tc.ordering[0]]
        tc.reorder(reordering)

        self.assertTrue(tc.ordering == reordered_uids)

        xforms = [transform3, transform2, transform1]
        reordered_xforms = [t for t in tc]
        self.assertTrue(xforms == reordered_xforms)

    def test_basic_data_wrapper(self):

        def transform1a(df):
            df['A'] = df['A'] + 3.
            return df

        def transform2a(df):
            df['A'] = df['A'] + df['B']
            return df

        def transform1b(df):
            df['A'] = df['A'] * 3
            return df

        def transform2b(df):
            df['C'] = df['A'] + df['B'] * 2
            return df

        tc_a = TransformChain()
        tc_a.addtransform(transform1a)
        tc_a.addtransform(transform2a)

        tc_b = TransformChain()
        tc_b.addtransform(transform1b)
        tc_b.addtransform(transform2b)

        df = pd.DataFrame({'A': range(11), 'B': range(11)})
        wrapper = DataWrapper(df)
        df_a = wrapper.applychain(tc_a)
        df_b = wrapper.applychain(tc_b)

        df_a_true = deepcopy(df)
        df_a_true['A'] = df_a_true['A'] + 3.
        df_a_true['A'] = df_a_true['A'] + df_a_true['B']

        df_b_true = deepcopy(df)
        df_b_true['A'] = df_b_true['A'] * 3
        df_b_true['C'] = df_b_true['A'] + df_b_true['B'] * 2

        self.assertTrue(df_a.equals(df_a_true))
        self.assertTrue(df_b.equals(df_b_true))

        self.assertTrue(len(wrapper) == 2)

        self.assertTrue(df_a.equals(wrapper.modified[tc_a.uid]))
        self.assertTrue(df_b.equals(wrapper.modified[tc_b.uid]))
