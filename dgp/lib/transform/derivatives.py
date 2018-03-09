# coding: utf-8

import numpy as np
from scipy.signal import convolve


def central_difference(data_in, n=1, order=2, dt=0.1):
    """ central difference differentiator """
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

    return np.pad(dy, (1, 1), 'edge')


# TODO: Add option to specify order
def taylor_fir(data_in, n=1, dt=0.1):
    """ 10th order Taylor series FIR differentiator """
    coeff = np.array([1 / 1260, -5 / 504, 5 / 84, -5 / 21, 5 / 6, 0, -5 / 6, 5 / 21, -5 / 84, 5 / 504, -1 / 1260])
    x = data_in
    for _ in range(1, n + 1):
        y = convolve(x, coeff, mode='same')
        x = y
    return y * (1/dt)**n
