# coding: utf-8

import numpy as np


def central_difference(data_in, n=1, order=2, dt=0.1):
    if order == 2:
        # first derivative
        if n == 1:
            dy = (data_in[2:] - data_in[0:-2]) / (2 * dt)
        # second derivative
        elif n == 2:
            dy = ((data_in[0:-2] - 2 * data_in[1:-1] + data_in[2:]) /
                  np.power(dt, 2))
        else:
            raise ValueError('Invalid value for parameter n {1 or 2}')
    else:
        raise NotImplementedError

    # return np.pad(dy, (1, 1), 'edge')
    return dy


def gradient(data_in, dt=0.1):
    return np.gradient(data_in, dt)
