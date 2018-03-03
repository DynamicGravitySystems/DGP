# coding: utf-8

from .graph import TransformGraph
from .gravity import eotvos_correction, latitude_correction, free_air_correction
from .operators import concat


class StandardGravityGraph(TransformGraph):
    def __init__(self, trajectory):
        self.transform_graph = {'trajectory': trajectory,
                                'eotvos': (eotvos_correction, 'trajectory'),
                                'lat_corr': (latitude_correction, 'trajectory'),
                                'fac': (free_air_correction, 'trajectory'),
                                'total_corr': (sum, ['eotvos', 'lat_corr', 'fac']),
                                'new_frame': (concat, ['eotvos', 'lat_corr', 'fac', 'total_corr'])
                                }
        super().__init__()
