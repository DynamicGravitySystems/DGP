# coding: utf-8
# This file is part of DynamicGravityProcessor (https://github.com/DynamicGravitySystems/DGP). License is Apache v2

import numpy as np
from numpy import array


def derivative(y: array, datarate, edge_order=None):
    """
    Based on Matlab function 'd' Created by Sandra Martinka, August 2001
    Function to numerically estimate the nth time derivative of y
    In both cases of n len(dy) = len(y) - 2 :: One element from each end is lost in calculation
    usage dy = derivative(y, n, datarate)

    :param y: Array input
    :param datarate: Scalar data sampling rate in Hz
    :param edge_order: nth time derivative 1, 2 or None. If None return tuple of first and second order time derivatives
    :return: nth time derivative of y
    """
    if edge_order is None:
        d1 = derivative(y, 1, datarate)
        d2 = derivative(y, 2, datarate)
        return d1, d2

    if edge_order == 1:
        dy = (y[2:] - y[0:-2]) * (datarate / 2)
        return dy
    elif edge_order == 2:
        dy = ((y[0:-2] - 2 * y[1:-1]) + y[2:]) * (np.power(datarate, 2))
        return dy
    else:
        return ValueError('Invalid value for parameter n {1 or 2}')


# TODO: Need sample input to test
def calc_eotvos(lat: array, lon: array, ht: array, datarate: float, a=None, ecc=None, derivation_func=np.gradient):
    """
    calc_eotvos: Calculate Eotvos Gravity Corrections

    Based on Matlab function 'calc_eotvos_full Created by Sandra Preaux, NGS, NOAA August 24, 2009

    References
    ----------
    Harlan 1968, "Eotvos Corrections for Airborne Gravimetry" JGR 73,n14

    Parameters
    ----------
    lat : Array
        Array of geodetic latitude in decimal degrees
    lon : Array
        Array of longitude in decimal degrees
    ht : Array
        Array of ellipsoidal height in meters
    datarate : Float (Scalar)
        Scalar data rate in Hz
    a : Float (Scalar)
        Scalar semi-major axis of ellipsoid in meters
    ecc : Float (Scalar)
        Scalar eccentricity of ellipsoid
    derivation_func : Callable (Array, Scalar, Int)
        Callable function used to calculate first and second order time derivatives.

    Returns
    -------
    6-Tuple (Array, ...)
        Eotvos values in mgals
        Tuple(E: Array, rdoubledot, angular acc of ref frame, coriolis, centrifugal, centrifugal acc of earth)
    """
    if derivation_func is not np.gradient:
        bounds = slice(1, -1)
    else:
        bounds = slice(None, None, None)

    # Constants
    # TODO: Allow a and ecc to be specified in kwargs
    a = 6378137.0  # Default semi-major axis
    b = 6356752.3142  # Default semi-minor axis
    ecc = (a - b) / a  # Eccentricity (eq 5 Harlan)
    We = 0.00007292115  # sidereal rotation rate, radians/sec
    mps2mgal = 100000  # m/s/s to mgal

    # Convert lat/lon in degrees to radians
    rad_lat = np.deg2rad(lat)
    rad_lon = np.deg2rad(lon)

    dlat = derivation_func(rad_lat, datarate, edge_order=1)
    ddlat = derivation_func(rad_lat, datarate, edge_order=2)
    dlon = derivation_func(rad_lon, datarate, edge_order=1)
    ddlon = derivation_func(rad_lon, datarate, edge_order=2)
    dht = derivation_func(ht, datarate, edge_order=1)
    ddht = derivation_func(ht, datarate, edge_order=2)

    # Calculate sin(lat), cos(lat), sin(2*lat), and cos(2*lat)
    # Beware MATLAB uses an array index starting with one (1), whereas python uses zero indexed arrays
    sin_lat = np.sin(rad_lat[bounds])
    cos_lat = np.cos(rad_lat[bounds])
    sin_2lat = np.sin(2.0 * rad_lat[bounds])
    cos_2lat = np.cos(2.0 * rad_lat[bounds])

    # Calculate the r' and its derivatives
    r_prime = a * (1.0-ecc * sin_lat * sin_lat)
    dr_prime = -a * dlat * ecc * sin_2lat
    # matlab: ddrp=-a.*ddlat.*ecc.*sin2lat-2.0.*a.*dlat.*dlat.*ecc.*cos2lat;
    ddr_prime = -a * ddlat * ecc * sin_2lat - 2.0 * a * dlat * dlat * ecc * cos_2lat

    # Calculate the deviation from the normal and its derivatives
    D = np.arctan(ecc * sin_2lat)
    dD = 2.0 * dlat * ecc * cos_2lat
    ddD = 2.0 * ddlat * ecc * cos_2lat - 4.0 * dlat * dlat * ecc * sin_2lat

    # Calculate r and its derivatives
    r = array([
        -r_prime * np.sin(D),
        np.zeros(r_prime.size),
        -r_prime * np.cos(D)-ht[bounds]
    ])
    # rdot=[(-drp.*sin(D)-rp.*dD.*cos(D));zeros(size(rp));(-drp.*cos(D)+rp.*dD.*sin(D)-dht)];
    rdot = array([
        (-dr_prime * np.sin(D) - r_prime * dD * np.cos(D)),
        np.zeros(r_prime.size),
        (-dr_prime * np.cos(D) + r_prime * dD * np.sin(D) - dht)
    ])
    # ci=(-ddrp.*sin(D)-2.0.*drp.*dD.*cos(D)-rp.*(ddD.*cos(D)-dD.*dD.*sin(D)));
    ci = (-ddr_prime * np.sin(D) - 2.0 * dr_prime * dD * np.cos(D) - r_prime *
          (ddD * np.cos(D) - dD * dD * np.sin(D)))
    # ck = (-ddrp. * cos(D) + 2.0. * drp. * dD. * sin(D) + rp. * (ddD. * sin(D) + dD. * dD. * cos(D)) - ddht);
    ck = (-ddr_prime * np.cos(D) + 2.0 * dr_prime * dD * np.sin(D) + r_prime *
          (ddD * np.sin(D) + dD * dD * np.cos(D)) - ddht)
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

    # Calculate wexwexre (which is the centrifugal acceleration due to the earth)
    re = array([
        -r_prime * np.sin(D),
        np.zeros(r_prime.size),
        -r_prime * np.cos(D)
    ])
    we = array([
        We * cos_lat,
        np.zeros(sin_lat.shape),
        -We * sin_lat
    ])
    wexre = np.cross(we, re, axis=0)
    wexwexre = np.cross(we, wexre, axis=0)
    wexr = np.cross(we, r, axis=0)
    wexwexr = np.cross(we, wexr, axis=0)

    # Calculate total acceleration for the aircraft
    acc = r2dot + w2_x_rdot + wdot_x_r + wxwxr

    # Eotvos correction is the vertical component of the total acceleration of
    # the aircraft - the centrifugal acceleration of the earth, converted to mgal
    E = (acc[2] - wexwexr[2]) * mps2mgal
    if derivation_func is not np.gradient:
        E = np.pad(E, (1, 1), 'edge')
    # TODO: Pad the start/end due to loss during derivative computation (not necessary using np.gradient)

    # Return Eotvos corrections
    return E, r2dot, w2_x_rdot, wdot_x_r, wxwxr, wexwexr
