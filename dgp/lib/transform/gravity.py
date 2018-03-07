# coding: utf-8

import numpy as np
import pandas as pd
from numpy import array

from .derivatives import central_difference, taylor_fir
from ..etc import align_frames
from ..timesync import find_time_delay, shift_frame

# constants
a = 6378137.0  # Default semi-major axis
b = 6356752.3142  # Default semi-minor axis
ecc = (a - b) / a  # Eccentricity
We = 0.00007292115  # sidereal rotation rate, radians/sec
mps2mgal = 100000  # m/s/s to mgal


def gps_velocities(data_in, differentiator=central_difference):
    # phi
    lat = np.deg2rad(data_in['lat'].values)

    # lambda
    lon = np.deg2rad(data_in['long'].values)

    h = data_in['ell_ht'].values

    cn = a / np.sqrt(1 - (ecc * np.sin(lat))**2)
    cm = ((1 - ecc**2) / a**2) * cn**3
    lon_dot = differentiator(lon)
    lat_dot = differentiator(lat)
    ve = (cn + h) * np.cos(lat) * lon_dot
    vn = (cm + h) * lat_dot
    hdot = differentiator(h)
    ve_s = pd.Series(ve, name='ve', index=data_in.index)
    vn_s = pd.Series(vn, name='vn', index=data_in.index)
    vu_s = pd.Series(hdot, name='vu', index=data_in.index)

    return ve_s, vn_s, vu_s


def gps_acceleration(data_in, differentiator=central_difference):
    h = data_in['ell_ht'].values
    hddot = differentiator(h, n=2) * mps2mgal

    return pd.Series(hddot, name='gps_accel', index=data_in.index)


def fo_eotvos(data_in, differentiator=central_difference):
    lat = np.deg2rad(data_in['lat'].values)
    h = data_in['ell_ht'].values

    ve, vn, vu = gps_velocities(data_in, differentiator=differentiator)

    term1 = vn ** 2 / a * (1 - h / a + ecc * (2 - 3 * np.sin(lat) ** 2))
    term2 = ve ** 2 / a * (1 - h / a - ecc * np.sin(lat) ** 2) + 2 * We * ve * np.cos(lat)

    return (term1 + term2) * mps2mgal


def kinematic_accel(data_in):
    eotvos = fo_eotvos(data_in, differentiator=taylor_fir)
    gps_accel = gps_acceleration(data_in, differentiator=taylor_fir)
    gps_accel = gps_accel.iloc[10:-10].copy()
    eotvos, gps_accel = align_frames(eotvos, gps_accel)

    return eotvos - gps_accel


def eotvos_correction(data_in):
    """
    Eotvos correction

    Parameters
    ----------
        data_in: DataFrame
            trajectory frame containing latitude, longitude, and
            height above the ellipsoid
        dt: float
            sample period

    Returns
    -------
        Series
            index taken from the input

    Notes
    -----
    Added to observed gravity when the positive direction of the sensitive axis is
    down, otherwise, subtracted.

    References
    ---------
    Harlan 1968, "Eotvos Corrections for Airborne Gravimetry" JGR 73,n14
    """

    dt = 0.1

    lat = np.deg2rad(data_in['lat'].values)
    lon = np.deg2rad(data_in['long'].values)
    ht = data_in['ell_ht'].values

    dlat = central_difference(lat, n=1, dt=dt)
    ddlat = central_difference(lat, n=2, dt=dt)
    dlon = central_difference(lon, n=1, dt=dt)
    ddlon = central_difference(lon, n=2, dt=dt)
    dht = central_difference(ht, n=1, dt=dt)
    ddht = central_difference(ht, n=2, dt=dt)

    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)
    sin_2lat = np.sin(2.0 * lat)
    cos_2lat = np.cos(2.0 * lat)

    # Calculate the r' and its derivatives
    r_prime = a * (1.0 - ecc * sin_lat * sin_lat)
    dr_prime = -a * dlat * ecc * sin_2lat
    ddr_prime = (-a * ddlat * ecc * sin_2lat - 2.0 * a *
                 dlat * dlat * ecc * cos_2lat)

    # Calculate the deviation from the normal and its derivatives
    D = np.arctan(ecc * sin_2lat)
    dD = 2.0 * dlat * ecc * cos_2lat
    ddD = (2.0 * ddlat * ecc * cos_2lat - 4.0 * dlat * dlat *
           ecc * sin_2lat)

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

    # total acceleration
    acc = r2dot + w2_x_rdot + wdot_x_r + wxwxr

    # vertical component of aircraft acceleration
    E = (acc[2] - wexwexr[2]) * mps2mgal
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
       :obj:`Series`
           units are mGal

    Notes
    -----
    Added to observed gravity when the positive direction of the sensitive axis is
    down, otherwise, subtracted.
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
        :obj:`Series`
            units are mGal

    Notes
    -----
    Added to observed gravity when the positive direction of the sensitive axis is
    down, otherwise, subtracted.
    """
    lat = np.deg2rad(data_in['lat'].values)
    ht = data_in['ell_ht'].values
    sin_lat2 = np.sin(lat) ** 2
    fac = ((np.float(0.3087691) - np.float(0.0004398) * sin_lat2) *
           ht) - np.float(7.2125e-8) * (ht ** 2)
    return pd.Series(fac, index=data_in.index, name='fac')