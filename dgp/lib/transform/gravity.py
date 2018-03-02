# coding: utf-8

import numpy as np
import pandas as pd
from numpy import array

from .derivatives import centraldifference


def eotvos_correction(data_in):
    """
        Eotvos correction

        Parameters
        ----------
            data_in: DataFrame
                trajectory frame containing latitude, longitude, and
                height above the ellipsoid

        Returns
        -------
            Series
                using the index from the input
    """
    lat = np.deg2rad(data_in['lat'].values)
    lon = np.deg2rad(data_in['long'].values)
    ht = data_in['ell_ht'].values

    dlat = centraldifference(lat, n=1, dt=self.dt)
    ddlat = centraldifference(lat, n=2, dt=self.dt)
    dlon = centraldifference(lon, n=1, dt=self.dt)
    ddlon = centraldifference(lon, n=2, dt=self.dt)
    dht = centraldifference(ht, n=1, dt=self.dt)
    ddht = centraldifference(ht, n=2, dt=self.dt)

    # dlat = gradient(lat)
    # ddlat = gradient(dlat)
    # dlon = gradient(lon)
    # ddlon = gradient(dlon)
    # dht = gradient(ht)
    # ddht = gradient(dht)

    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)
    sin_2lat = np.sin(2.0 * lat)
    cos_2lat = np.cos(2.0 * lat)

    # Calculate the r' and its derivatives
    r_prime = self.a * (1.0 - self.ecc * sin_lat * sin_lat)
    dr_prime = -self.a * dlat * self.ecc * sin_2lat
    ddr_prime = (-self.a * ddlat * self.ecc * sin_2lat - 2.0 * self.a *
                 dlat * dlat * self.ecc * cos_2lat)

    # Calculate the deviation from the normal and its derivatives
    D = np.arctan(self.ecc * sin_2lat)
    dD = 2.0 * dlat * self.ecc * cos_2lat
    ddD = (2.0 * ddlat * self.ecc * cos_2lat - 4.0 * dlat * dlat *
           self.ecc * sin_2lat)

    # Calculate this value once (used many times)
    sinD = np.sin(D)
    cosD = np.cos(D)

    # Calculate r and its derivatives
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
        (dlon + self.We) * cos_lat,
        -dlat,
        (-(dlon + self.We)) * sin_lat
    ])

    wdot = array([
        dlon * cos_lat - (dlon + self.We) * dlat * sin_lat,
        -ddlat,
        (-ddlon * sin_lat - (dlon + self.We) * dlat * cos_lat)
    ])

    w2_x_rdot = np.cross(2.0 * w, rdot, axis=0)
    wdot_x_r = np.cross(wdot, r, axis=0)
    w_x_r = np.cross(w, r, axis=0)
    wxwxr = np.cross(w, w_x_r, axis=0)

    we = array([
        self.We * cos_lat,
        np.zeros(sin_lat.shape),
        -self.We * sin_lat
    ])

    wexr = np.cross(we, r, axis=0)
    wexwexr = np.cross(we, wexr, axis=0)

    # Calculate total acceleration for the aircraft
    acc = r2dot + w2_x_rdot + wdot_x_r + wxwxr

    E = (acc[2] - wexwexr[2]) * self.mps2mgal
    return pd.Series(E, index=data_in.index, name='eotvos')



def latitude_correction(data_in):
    """
       WGS84 latitude correction

       Accounts for the Earth's elliptical shape and rotation. The gravity value
       that would be observed if Earth were a perfect, rotating ellipsoid is
       referred to as normal gravity. Gravity increases with increasing latitude.
       The correction is added as one moves toward the equator.

       Parameters
       ----------
           data_in: DataFrame
               trajectory frame containing latitude, longitude, and
               height above the ellipsoid

       Returns
       -------
           Series
               units are mGal
       """
    lat = np.deg2rad(data_in['lat'].values)
    sin_lat2 = np.sin(lat) ** 2
    num = 1 + np.float(0.00193185265241) * sin_lat2
    den = np.sqrt(1 - np.float(0.00669437999014) * sin_lat2)
    corr = -np.float(978032.53359) * num / den
    return pd.Series(corr, index=data_in.index, name='lat_corr')


def free_air_correction(data_in):
    """
    2nd order Free Air Correction

    Compensates for the change in the gravitational field with respect to
    distance from the center of the ellipsoid. Does not include the effect
    of mass between the observation point and the datum.

    Parameters
    ----------
        data_in: :class:`DataFrame`
            trajectory frame containing latitude, longitude, and
            height above the ellipsoid

    Returns
    -------
        :class:`Series`
            units are mGal
    """
    lat = np.deg2rad(data_in['lat'].values)
    ht = data_in['ell_ht'].values
    sin_lat2 = np.sin(lat) ** 2
    fac = -((np.float(0.3087691) - np.float(0.0004398) * sin_lat2) *
            ht) + np.float(7.2125e-8) * (ht ** 2)
    return pd.Series(fac, index=data_in.index, name='fac')