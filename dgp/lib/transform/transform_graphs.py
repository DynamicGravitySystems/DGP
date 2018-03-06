# coding: utf-8
from functools import partial
import pandas as pd

from .graph import TransformGraph
from .gravity import (eotvos_correction, latitude_correction,
                      free_air_correction)
from.filters import lp_filter, detrend


class AirbornePost(TransformGraph):

    concat = partial(pd.concat, axis=1, join='outer')

    def total_corr(self, *args):
        return pd.Series(sum(*args), name='total_corr')

    def mult(self, a, b):
        return pd.Series(a * b, name='abs_grav')

    def corrected_grav(self, *args):
        return pd.Series(sum(*args), name='corrected_grav')

    def __init__(self, trajectory, gravity, begin_static, end_static, tie):
        self.begin_static = begin_static
        self.end_static = end_static
        self.gravity_tie = tie
        self.transform_graph = {'trajectory': trajectory,
                                'gravity': gravity,
                                'eotvos': (eotvos_correction, 'trajectory'),
                                'lat_corr': (latitude_correction, 'trajectory'),
                                'fac': (free_air_correction, 'trajectory'),
                                'total_corr': (self.total_corr, ['eotvos', 'lat_corr', 'fac']),
                                'begin_static': self.begin_static,
                                'end_static': self.end_static,
                                'gravity_channel': gravity['gravity'],
                                'grav_dedrift': (detrend, 'gravity_channel', 'begin_static', 'end_static'),
                                'gravity_tie': self.gravity_tie,
                                'abs_grav': (self.mult, 'gravity_tie', 'grav_dedrift'),
                                'corrected_grav': (self.corrected_grav, 'total_corr', 'abs_grav'),
                                'filtered_grav': (lp_filter, 'corrected_grav'),
                                'new_frame': (self.concat, ['eotvos', 'lat_corr', 'fac', 'total_corr', 'abs_grav',
                                                            'filtered_grav'])
                                }
        super().__init__()
