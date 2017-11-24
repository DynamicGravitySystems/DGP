# coding=utf-8

"""
derivative.py
Library for derivative classes

"""

import numpy as np
from numpy import array

from dgp.lib.transform import Transform, Derivative


class CentralDiff2(Derivative):
    """
    Based on Matlab function 'd' Created by Sandra Martinka, August 2001
    Central difference of order O(h^4)
    Function to numerically estimate the nth time derivative of y
    In both cases for n, len(dy) = len(y) - 4. Two elements from each end are
    lost in calculation.

    Parameters
    ----------
        y : array_like
            input
        datarate : float
            data sampling rate in Hz
        n : int
            nth time derivative 1, 2.

    Returns
    -------
        array_like
            first or second time derivative of y
    """
    var_dict = {'datarate', '_datarate'}

    def __init__(self, datarate=10):
        super().__init__(self.func)
        self.name = u'central difference'
        self.order = 2
        self._datarate = datarate

    @property
    def datarate(self):
        return self._datarate

    @datarate.setter
    def datarate(self, d):
        self._datarate = d

    def func(self, y: array, n=1):
        # first derivative
        if n == 1:
            dy = (y[2:] - y[0:-2]) * (self._datarate / 2)
        # second derivative
        elif n == 2:
            dy = (y[0:-2] - 2 * y[1:-1] + y[2:]) * np.power(self._datarate, 2)
        else:
            raise ValueError('Invalid value for parameter n {1 or 2}')

        return np.pad(dy, (1, 1), 'edge')


class Eotvos(Transform):
    """
    Calculate Eotvos Gravity Corrections

    Based on Matlab function 'calc_eotvos_full Created by Sandra Preaux, NGS, NOAA August 24, 2009

    References
    ----------
    Harlan 1968, "Eotvos Corrections for Airborne Gravimetry" JGR 73,n14

    Parameters
    ----------
    lat : array-like
        Array of geodetic latitude in decimal degrees
    lon : array-like
        Array of longitude in decimal degrees
    ht : array-like
        Array of ellipsoidal height in meters
    datarate : float
        Data rate in Hz
    derivation_func : `callable`
        Callable function used to calculate first and second order time derivatives.
    kwargs
        a : float
            Specify semi-major axis
        ecc : float
            Eccentricity

    Returns
    -------
    6-Tuple (array-like, ...)
        Eotvos values in mgals
        Tuple(E: Array, rdoubledot, angular acc of ref frame, coriolis, centrifugal, centrifugal acc of earth)
    """

    _var_dict = {}

    def __init__(self, derivative: Derivative, **kwargs):
        super().__init__(self.func, 'correction', self._var_dict)
        self.name = u'Eötvös correction'
        self.derivative = derivative

    def func(self, lat: array, lon: array, ht: array, **kwargs):
        # Constants
        # a = 6378137.0  # Default semi-major axis
        a = kwargs.get('a', 6378137.0)  # Default semi-major axis
        b = 6356752.3142  # Default semi-minor axis
        ecc = kwargs.get('ecc', (a - b) / a)  # Eccentricity

        We = 0.00007292115  # sidereal rotation rate, radians/sec
        mps2mgal = 100000  # m/s/s to mgal

        # Convert lat/lon in degrees to radians
        lat = np.deg2rad(lat)
        lon = np.deg2rad(lon)

        dlat = self.derivative(lat, n=1)
        ddlat = self.derivative(lat, n=2)
        dlon = self.derivative(lon, n=1)
        ddlon = self.derivative(lon, n=2)
        dht = self.derivative(ht, n=1)
        ddht = self.derivative(ht, n=2)

        # Calculate sin(lat), cos(lat), sin(2*lat), and cos(2*lat)
        # sin_lat = np.sin(lat[bounds])
        # cos_lat = np.cos(lat[bounds])
        # sin_2lat = np.sin(2.0 * lat[bounds])
        # cos_2lat = np.cos(2.0 * lat[bounds])
        sin_lat = np.sin(lat)
        cos_lat = np.cos(lat)
        sin_2lat = np.sin(2.0 * lat)
        cos_2lat = np.cos(2.0 * lat)

        # Calculate the r' and its derivatives
        r_prime = a * (1.0 - ecc * sin_lat * sin_lat)
        dr_prime = -a * dlat * ecc * sin_2lat
        ddr_prime = -a * ddlat * ecc * sin_2lat - 2.0 * a * dlat * dlat * ecc * cos_2lat

        # Calculate the deviation from the normal and its derivatives
        D = np.arctan(ecc * sin_2lat)
        dD = 2.0 * dlat * ecc * cos_2lat
        ddD = 2.0 * ddlat * ecc * cos_2lat - 4.0 * dlat * dlat * ecc * sin_2lat
        # Calculate this value once (used many times)
        sinD = np.sin(D)
        cosD = np.cos(D)

        # Calculate r and its derivatives
        # r = array([
        #     -r_prime * sinD,
        #     np.zeros(r_prime.size),
        #     -r_prime * cosD-ht[bounds]
        # ])
        r = array([
            -r_prime * sinD,
            np.zeros(r_prime.size),
            -r_prime * cosD - ht
        ])

        rdot = array([
            (-dr_prime * sinD - r_prime * dD * cosD),
            np.zeros(r_prime.size),
            (-dr_prime * cosD + r_prime * dD * sinD - dht)
        ])
        ci = (-ddr_prime * sinD - 2.0 * dr_prime * dD * cosD - r_prime *
              (ddD * cosD - dD * dD * sinD))
        ck = (-ddr_prime * cosD + 2.0 * dr_prime * dD * sinD + r_prime *
              (ddD * sinD + dD * dD * cosD) - ddht)
        r2dot = array([
            ci,
            np.zeros(ci.size),
            ck
        ])

        # Define w and its derivative
        w = array([
            (dlon + We) * cos_lat,
            -dlat,
            (-(dlon + We)) * sin_lat
        ])
        wdot = array([
            dlon * cos_lat - (dlon + We) * dlat * sin_lat,
            -ddlat,
            (-ddlon * sin_lat - (dlon + We) * dlat * cos_lat)
        ])
        w2_x_rdot = np.cross(2.0 * w, rdot, axis=0)
        wdot_x_r = np.cross(wdot, r, axis=0)
        w_x_r = np.cross(w, r, axis=0)
        wxwxr = np.cross(w, w_x_r, axis=0)

        we = array([
            We * cos_lat,
            np.zeros(sin_lat.shape),
            -We * sin_lat
        ])

        wexr = np.cross(we, r, axis=0)
        wexwexr = np.cross(we, wexr, axis=0)

        # Calculate total acceleration for the aircraft
        acc = r2dot + w2_x_rdot + wdot_x_r + wxwxr

        # Eotvos correction is the vertical component of the total acceleration of
        # the aircraft - the centrifugal acceleration of the earth, converted to mgal
        E = (acc[2] - wexwexr[2]) * mps2mgal

        # if derivation_func is not np.gradient:
        #     E = np.pad(E, (1, 1), 'edge')

        # Return Eotvos corrections
        return E
