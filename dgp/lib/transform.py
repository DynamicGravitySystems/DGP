# coding=utf-8

"""
transform.py
Library for data transformation classes

"""

from copy import deepcopy
from collections import defaultdict
from pandas import DataFrame

from dgp.lib.etc import gen_uuid

class TransformChain:
    def __init__(self):
        self._uid = gen_uuid('tc')
        self.transforms = {}
        self.ordering = []

    @property
    def uid(self):
        return self._uid

    def addtransform(self, transform):
        if callable(transform):
            uid = gen_uuid('tf')
            self.transforms[uid] = transform
            self.ordering.append(uid)
            return uid
        else:
            return None

    def removetransform(self, uid):
        del self.transforms[uid]
        self.ordering.remove(uid)

    def reorder(self, reordering):
        """
        Change the order of application of transforms. Input is a dictionary
        with transform uid's as keys and position as values.
        """
        order = sorted(reordering.values(), key=reordering.__get_item__)
        for uid in order:
            self.ordering.remove(uid)
            self.ordering.insert(reordering[uid], uid)
        return self.ordering

    def apply(self, df):
        """
        Makes a deep copy of the target DataFrame and applies the transforms in
        the order specified.
        """
        df_cp = deepcopy(df)
        for uid in self.ordering:
            df_cp = self.transforms[uid](df_cp)
        return df_cp

    def __len__(self):
        return len(self.transforms.items())

    def __str__(self):
        return 'TransformChain({uid})'.format(uid=self._uid)

class DataWrapper:
    """
    A container for transformed DataFrames. Multiple transform chains may
    be specified and the resultant DataFrames will be held in this class instance.
    """
    def __init__(self, frame: DataFrame):
        self.df = frame # original DataFrame; not ever modified
        self.modified = {}
        self._transform_chains = {}

    def removechain(self, uid):
        del self._transform_chains[uid]
        del self.modified[uid]

    def applychain(self, tc):
        if not isinstance(tc, TransformChain):
            raise TypeError('expected an instance of subclass of TransformChain, but got ({typ})'.format(type(tc)))

        if tc.uid not in self._transform_chains:
            self._transform_chains[tc.uid] = tc
        self.modified[tc.uid] = self._transform_chains[tc.uid].apply(self.df)
        return self.modified[tc.uid]

    def __len__(self):
        return len(self.modified.items())
