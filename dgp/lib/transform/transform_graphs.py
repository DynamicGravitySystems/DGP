# coding: utf-8

from .graph import TransformGraph
from .gravity import eotvos_correction, latitude_correction, free_air_correction


class StandardGravityGraph(TransformGraph):
    def __init__(self, gravity, trajectory):
        graph = {'gravity': gravity,
                 'trajectory': trajectory,
                 'dt': 0.1,
                 'eotvos': (eotvos_correction, 'trajectory', 'dt'),
                 'lat_corr': (latitude_correction, 'trajectory'),
                 'fac': (free_air_correction, 'trajectory'),
                 'total_corr': (sum, ['eotvos', 'lat_corr', 'fac'])
                 }

        super(StandardGravityGraph, self).__init__(graph)