# coding: utf-8
from functools import partial
import pandas as pd

from .graph import TransformGraph
from .gravity import (eotvos_correction, latitude_correction,
                      free_air_correction, kinematic_accel)
from .filters import lp_filter, detrend
from ..timesync import find_time_delay, shift_frame
from ..etc import align_frames


class SyncGravity(TransformGraph):

    # TODO: align_frames only works with this ordering, but should work for either
    def __init__(self, trajectory, gravity):
        self.transform_graph = {'trajectory': trajectory,
                                'gravity': gravity,
                                'raw_grav': gravity['gravity'],
                                'kin_accel': (kinematic_accel, 'trajectory'),
                                'delay': (find_time_delay, 'kin_accel', 'raw_grav'),
                                'shifted_gravity': (shift_frame, 'gravity', 'delay'),
                                }

        super().__init__()


class AirbornePost(TransformGraph):

    concat = partial(pd.concat, axis=1, join='outer')

    def total_corr(self, *args):
        return pd.Series(sum(*args), name='total_corr')

    def corrected_grav(self, *args):
        return pd.Series(sum(*args), name='corrected_grav')

    def demux(self, df, col):
        return df[col]

    # TODO: What if a function takes a string argument? Use partial for now.
    # TODO: Little tricky to debug these graphs. Breakpoints? Print statements?
    # TODO: Fix detrending for a section of flight
    def __init__(self, trajectory, gravity, begin_static, end_static, tie, k):
        self.begin_static = begin_static
        self.end_static = end_static
        self.gravity_tie = tie
        self.k_factor = k
        self.transform_graph = {'trajectory': trajectory,
                                'gravity': gravity,
                                'shifted_gravity': (SyncGravity.run(item='shifted_gravity'), 'trajectory', 'gravity'),
                                'shifted_trajectory': (partial(align_frames, item='r'), 'shifted_gravity', 'trajectory'),
                                'eotvos': (eotvos_correction, 'shifted_trajectory'),
                                'lat_corr': (latitude_correction, 'shifted_trajectory'),
                                'fac': (free_air_correction, 'shifted_trajectory'),
                                'total_corr': (self.total_corr, ['eotvos', 'lat_corr', 'fac']),
                                'abs_grav': (partial(self.demux, col='gravity'), 'shifted_gravity'),
                                'corrected_grav': (self.corrected_grav, ['total_corr', 'abs_grav']),
                                'filtered_grav': (partial(lp_filter, fs=10), 'corrected_grav'),
                                'new_frame': (self.concat, ['eotvos', 'lat_corr', 'fac', 'total_corr', 'abs_grav', 'filtered_grav'])
                                }
        super().__init__()
