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
                                'eotvos_and_accel': (partial(eotvos_correction, differentiator=central_difference), 'trajectory'),
                                'eotvos': (partial(demux, col='eotvos'), 'eotvos_and_accel'),
                                'kin_accel': (partial(demux, col='kin_accel'), 'eotvos_and_accel'),
                                'aligned_eotvos': (partial(align_frames, item='r'), 'trajectory', 'eotvos'),
                                'aligned_kin_accel': (partial(align_frames, item='r'), 'trajectory', 'kin_accel'),
                                'lat_corr': (latitude_correction, 'trajectory'),
                                'fac': (free_air_correction, 'trajectory'),
                                'total_corr': (self.total_corr, ['aligned_kin_accel', 'aligned_eotvos', 'lat_corr', 'fac']),
                                'abs_grav': (partial(demux, col='gravity'), 'gravity'),
                                'corrected_grav': (self.corrected_grav, ['total_corr', 'abs_grav']),
                                'filtered_grav': (partial(lp_filter, fs=10), 'corrected_grav')
                                }
        super().__init__()

# class ExampleGraph(TransformGraph):
#     inputs = ('trajectory', 'gravity', 'begin_static', 'end_static')
#     graph = {
#         ('gravity', 'trajectory'): (align_frames(item='r'), 'gravity', 'trajectory'),
#         ('eotvos', 'accel'): (eotvos_correction, 'trajectory'),
#         'lat_corr': (latitude_correction, 'trajectory'),
#         'fac': (free_air_correction, 'trajectory'),
#         'total_corr': (sum, ['eotvos', 'accel', 'lat_corr', 'fac']),
#         'corrected_grav': (sum, 'total_corr', demux('gravity', 'gravity')),
#         'filtered_grav': (lp_filter(fs=10), 'corrected_grav')
#     }
#
# @transformgraph
# def detrend(begin_static, end_static, data_in):
#     if hasattr(grav, 'index'):
#         length = len(data_in.index)
#     else:
#         length = len(data_in)
#
#     trend = np.linspace(begin, end, num=length)
#     if hasattr(data_in, 'sub'):
#         trend = pd.Series(trend, index=data_in.index)
#         result = data_in.sub(trend, axis=0)
#     else:
#         result = data_in - trend
#     return result
#
# # TODO: How to deal with keyword args?
# # should result in
# class Detrend(TransformGraph):
#     inputs = ('begin_static', 'end_static', 'data_in')
#     _func = detrend
#     graph = {
#         'result': (detrend, 'begin_static', 'end_static', 'data_in')
#     }