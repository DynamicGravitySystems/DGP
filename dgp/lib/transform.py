# coding=utf-8

"""
transform.py
Library for data transformation classes

"""

from copy import deepcopy
from pandas import DataFrame

from dgp.lib.etc import gen_uuid, dedup_dict

class TransformChain:
    def __init__(self):
        self._uid = gen_uuid('tc')
        self._transforms = {}
        self._ordering = []

    @property
    def uid(self):
        return self._uid

    @property
    def ordering(self):
        return self._ordering

    def addtransform(self, transform):
        if callable(transform):
            uid = gen_uuid('tf')
            self._transforms[uid] = transform
            self._ordering.append(uid)
            return (uid, self._transforms[uid])
        else:
            return None

    def removetransform(self, uid):
        del self._transforms[uid]
        self._ordering.remove(uid)

    def reorder(self, reordering):
        """
        Change the order of application of transforms. Input is a dictionary
        with transform uid's as keys and position as values.
        """
        d = dedup_dict(reordering)
        order = sorted(d.keys(), key=d.__getitem__)
        for uid in order:
            self._ordering.remove(uid)
            self._ordering.insert(d[uid], uid)
        return self.ordering

    def apply(self, df):
        """
        Makes a deep copy of the target DataFrame and applies the transforms in
        the order specified.
        """
        df_cp = deepcopy(df)
        for uid in self._ordering:
            df_cp = self._transforms[uid](df_cp)
        return df_cp

    def __len__(self):
        return len(self._transforms.items())

    def __str__(self):
        return 'TransformChain({uid})'.format(uid=self._uid)

    def __getitem__(self, key):
        return self._ordering[key]

    def __iter__(self):
        for uid in self._ordering:
            yield self._transforms[uid]

class DataWrapper:
    """
    A container for transformed DataFrames. Multiple transform chains may
    be specified and the resultant DataFrames will be held in this class
    instance.
    """
    def __init__(self, frame: DataFrame):
        self.df = frame # original DataFrame; not ever modified
        self.modified = {}
        self._transform_chains = {}
        self._defaultchain = None

    def removechain(self, uid):
        del self._transform_chains[uid]
        del self.modified[uid]

    def applychain(self, tc):
        if not isinstance(tc, TransformChain):
            raise TypeError('expected an instance or subclass of '
                            'TransformChain, but got ({typ})'.format(type(tc)))

        if tc.uid not in self._transform_chains:
            self._transform_chains[tc.uid] = tc
            if self._defaultchain is None:
                self._defaultchain = self._transform_chains[tc.uid]
        self.modified[tc.uid] = self._transform_chains[tc.uid].apply(self.df)
        return self.modified[tc.uid]

    @property
    def data(self, reapply=False):
        if self._defaultchain is not None:
            if reapply:
                return self.applychain(self._defaultchain)
            else:
                return self.modified[self._defaultchain.uid]
        else:
            return self.df

    def __len__(self):
        return len(self.modified.items())
