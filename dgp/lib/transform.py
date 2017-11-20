# coding=utf-8

"""
transform.py
Library for data transformation classes

"""

from copy import deepcopy
from pandas import DataFrame
import inspect

from dgp.lib.etc import gen_uuid, dedup_dict


class Transform:
    def __init__(self, func, typ):
        self._uid = gen_uuid('xf')
        self._func = func
        self._transformtype = typ

    @property
    def func(self):
        return self._func

    @property
    def transformtype(self):
        return self._transformtype

    @transformtype.setter
    def transformtype(self, type):
        self._transformtype = type

    @property
    def uid(self):
        return self._uid

    def __call__(self, *args, **kwargs):
        raise NotImplementedError('Abstract definition. Not implemented.')

    def __str__(self):
        return 'Transform({func})'.format(func=self._func)


class Filter(Transform):
    var_dict = {'fs': '_fs',
                'fc': '_fc',
                'order': '_order',
                'wn': '_wn',
                'nyq': '_nyq',
                'window': '_window'
                }

    def __init__(self, func, fc, fs, typ):
        super().__init__(func, 'filter')

        self.filtertype = typ
        self._window = 'blackman'
        self._fs = fs
        self._fc = fc

        self._order = 2.0 * 1 / self._fc * self._fs
        self._nyq = self._fs * 0.5
        self._wn = self._fc / self._nyq

    @property
    def nyq(self):
        return self._nyq

    @property
    def wn(self):
        return self._wn

    @property
    def fc(self):
        return self._fc

    @fc.setter
    def fc(self, f):
        self._fc = f
        self._order = 2.0 * 1 / self._fc * self._fs
        self._wn = self._fc / self._nyq

    @property
    def fs(self):
        return self._fs

    @property
    def window(self):
        return self._window

    @window.setter
    def window(self, w):
        # TODO: Check for valid window selection
        self._window = w

    @fs.setter
    def fs(self, f):
        self._fs = f
        self._order = 2.0 * 1 / self._fc * self._fs
        self._nyq = self._fs * 0.5
        self._wn = self._fc / self._nyq

    def __call__(self, *args, **kwargs):
        # identify arguments that are instance variables
        argspec = inspect.getfullargspec(self._func)
        keywords = {}
        for arg in argspec.args:
            if arg in self.var_dict:
                keywords[arg] = self.__dict__[self.var_dict[arg]]

        # override keywords explicitly set in function call
        for k, v in kwargs.items():
            keywords[k] = v

        return self._func(*args, **keywords)

    def __repr__(self):
        return """Filter type: {typ}
                  Window: {window}
                  Cutoff frequency: {fc} Hz
                  Sample frequency: {fs} Hz
                  Nyquist frequency: {nyq} Hz
                  Normalized frequency: {wn} pi radians / sample
                  Order: {order}
               """.format(typ=self.filtertype, fc=self._fc, fs=self._fs,
                          nyq=self._nyq, order=self._order, wn=self._wn,
                          window=self._window)


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
