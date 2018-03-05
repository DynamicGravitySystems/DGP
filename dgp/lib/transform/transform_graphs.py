# coding: utf-8
from functools import partial
import pandas as pd

from .graph import TransformGraph
from .gravity import eotvos_correction, latitude_correction, free_air_correction


class StandardGravityGraph(TransformGraph):

    concat = partial(pd.concat, axis=1, join='outer')

    def total_corr(self, *args):
        return pd.Series(sum(*args), name='total_corr')

    def __init__(self, trajectory):
        self.transform_graph = {'trajectory': trajectory,
                                'eotvos': (eotvos_correction, 'trajectory'),
                                'lat_corr': (latitude_correction, 'trajectory'),
                                'fac': (free_air_correction, 'trajectory'),
                                'total_corr': (self.total_corr, ['eotvos', 'lat_corr', 'fac']),
                                'new_frame': (self.concat, ['eotvos', 'lat_corr', 'fac', 'total_corr'])
                                }
        super().__init__()
