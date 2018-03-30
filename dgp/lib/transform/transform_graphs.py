# coding: utf-8
from functools import partial
import pandas as pd

from .graph import TransformGraph
from .gravity import (eotvos_correction, latitude_correction,
                      free_air_correction, kinematic_accel)
from .filters import lp_filter
from ..timesync import find_time_delay, shift_frame
from ..etc import align_frames
from .derivatives import taylor_fir, central_difference


def demux(df, col):
    return df[col]

class SyncGravity(TransformGraph):

    # TODO: align_frames only works with this ordering, but should work for either
    def __init__(self, kin_accel, gravity):
        self.transform_graph = {'gravity': gravity,
                                'raw_grav': gravity['gravity'],
                                'kin_accel': kin_accel,
                                'delay': (find_time_delay, 'kin_accel', 'raw_grav'),
                                'shifted_gravity': (shift_frame, 'gravity', 'delay'),
                                }

        super().__init__()


class AirbornePost(TransformGraph):

    # concat = partial(pd.concat, axis=1, join='outer')

    def total_corr(self, *args):
        return pd.Series(sum(*args), name='total_corr')

    def corrected_grav(self, *args):
        return pd.Series(sum(*args), name='corrected_grav')

    # TODO: What if a function takes a string argument? Use partial for now.
    # TODO: Little tricky to debug these graphs. Breakpoints? Print statements?
    def __init__(self, trajectory, gravity, begin_static, end_static):
        self.begin_static = begin_static
        self.end_static = end_static
        self.transform_graph = {'trajectory': trajectory,
                                'gravity': gravity,
                                'synced_gravity': (SyncGravity.run(item='shifted_gravity'), 'kin_accel', 'gravity'),
                                'shifted_trajectory': (partial(align_frames, item='r'), 'synced_gravity', 'trajectory'),
                                'shifted_gravity': (partial(align_frames, item='l'), 'synced_gravity', 'trajectory'),
                                'eotvos_and_accel': (partial(eotvos_correction, differentiator=central_difference), 'trajectory'),
                                'eotvos': (partial(demux, col='eotvos'), 'eotvos_and_accel'),
                                'kin_accel': (partial(demux, col='kin_accel'), 'eotvos_and_accel'),
                                'aligned_eotvos': (partial(align_frames, item='r'), 'shifted_trajectory', 'eotvos'),
                                'aligned_kin_accel': (partial(align_frames, item='r'), 'shifted_trajectory', 'kin_accel'),
                                'lat_corr': (latitude_correction, 'shifted_trajectory'),
                                'fac': (free_air_correction, 'shifted_trajectory'),
                                'total_corr': (self.total_corr, ['aligned_kin_accel', 'aligned_eotvos', 'lat_corr', 'fac']),
                                'abs_grav': (partial(demux, col='gravity'), 'shifted_gravity'),
                                'corrected_grav': (self.corrected_grav, ['total_corr', 'abs_grav']),
                                'filtered_grav': (partial(lp_filter, fs=10), 'corrected_grav')
                                }
        super().__init__()
