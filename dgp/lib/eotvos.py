# coding: utf-8

import numpy as np
from numpy import array


def derivative(y: array, datarate, n=None):
    """
    Based on Matlab function 'd' Created by Sandra Martinka, August 2001
    Function to numerically estimate the nth time derivative of y
    In both cases of n len(dy) = len(y) - 2 :: One element from each end is lost in calculation
    usage dy = derivative(y, n, datarate)

    :param y: Array input
    :param datarate: Scalar data sampling rate in Hz
    :param n: nth time derivative 1, 2 or None. If None return tuple of first and second order time derivatives
    :return: nth time derivative of y
    """
    if n is None:
        d1 = derivative(y, 1, datarate)
        d2 = derivative(y, 2, datarate)
        return d1, d2

    if n == 1:
        dy = (y[3:] - y[1:-2]) * (datarate / 2)
        return dy
    elif n == 2:
        dy = ((y[1:-2] - 2 * y[2:-1]) + y[3:]) * (np.power(datarate, 2))
        return dy
    else:
        return ValueError('Invalid value for parameter n {1 or 2}')


# TODO: Need sample input to test
def calc_eotvos(lat: array, lon: array, ht: array, datarate: float, a=None, ecc=None):
    """
    Based on Matlab function 'calc_eotvos_full Created by Sandra Preaux, NGS, NOAA August 24, 2009

    Usage:


    References:
        Harlan 1968, "Eotvos Corrections for Airborne Gravimetry" JGR 73,n14

    :param lat: Array geodetic latitude in decimal degrees
    :param lon: Array longitude in decimal degrees
    :param ht: ellipsoidal height in meters
    :param datarate: Scalar data rate in Hz
    :param a: Scalar semi-major axis of ellipsoid in meters
    :param ecc: Scalar eccentricity of ellipsoid
    :return: Tuple Eotvos values in mgals
        (rdoubledot, angular acceleration of the ref frame, coriolis, centrifugal, centrifugal acceleration of earth)
    """

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

    dlat, ddlat = derivative(rad_lat, datarate)
    dlon, ddlon = derivative(rad_lon, datarate)
    dht, ddht = derivative(ht, datarate)

    # Calculate sin(lat), cos(lat), sin(2*lat), and cos(2*lat)
    # Beware MATLAB uses an array index starting with one (1), whereas python uses zero indexed arrays
    sin_lat = np.sin(rad_lat[1:-1])
    cos_lat = np.cos(rad_lat[1:-1])
    sin_2lat = np.sin(2 * rad_lat[1:-1])
    cos_2lat = np.cos(2 * rad_lat[1:-1])

    # Calculate the r' and its derivatives
    r_prime = a * (1-ecc * sin_lat * sin_lat)
    dr_prime = a * dlat * ecc * sin_2lat
    ddr_prime = None

    # Calculate the deviation from the normal and its derivatives
    D = np.arctan(ecc * sin_2lat)
    dD = 2.0 * dlat * ecc * cos_2lat
    ddD = 2.0 * ddlat * ecc * cos_2lat - 4.0 * dlat * dlat * ecc * sin_2lat

    # Calculate r and its derivatives
    r = array([
        -r_prime * np.sin(D),
        np.zeros(r_prime.shape),
        -r_prime * np.cos(D)-ht[1:-1]
    ])
    rdot = array([
        -dr_prime * np.sin(D) - r_prime * dD * np.cos(D),
        np.zeros(r_prime.shape),
        -dr_prime * np.cos(D) + r_prime * dD * np.sin(D) - dht
    ])
    # ci=(-ddrp.*sin(D)-2.0.*drp.*dD.*cos(D)-rp.*(ddD.*cos(D)-dD.*dD.*sin(D)));
    ci = (-ddr_prime * np.sin(D) - 2.0 * dr_prime * dD * np.cos(D) - r_prime *
          (ddD * np.cos(D) - dD * dD * np.sin(D)))
    # ck = (-ddrp. * cos(D) + 2.0. * drp. * dD. * sin(D) + rp. * (ddD. * sin(D) + dD. * dD. * cos(D)) - ddht);
    ck = (-ddr_prime * np.cos(D) + 2.0 * dr_prime * dD * np.sin(D) + r_prime *
          (ddD * np.sin(D) + dD * dD * np.cos(D)) - ddht)
    r2dot = array([
        ci,
        np.zeros(ci.shape),
        ck
    ])

    # Define w and its derivative
    w = array([
        (dlon + We) * cos_lat,
        -dlat,
        -(dlon + We) * sin_lat
    ])
    wdot = array([
        dlon * cos_lat - (dlon + We) * dlat * sin_lat,
        -ddlat,
        (-ddlon * sin_lat - (dlon + We) * dlat * cos_lat)
    ])
    w2_x_rdot = np.cross(2.0 * w, rdot)
    wdot_x_r = np.cross(wdot, r)
    w_x_r = np.cross(w, r)
    wxwxr = np.cross(w, w_x_r)

    # Calculate wexwexre (that is the centrifugal acceleration due to the earth
    re = array([
        -r_prime * np.sin(D),
        np.zeros(r_prime.shape),
        -r_prime * np.cos(D)
    ])
    we = array([
        We * cos_lat,
        np.zeros(sin_lat.shape),
        -We * sin_lat
    ])
    we_x_re = np.cross(we, re)
    wexwexre = np.cross(we, we_x_re)
    we_x_r = np.cross(we, r)
    wexwexr = np.cross(we, we_x_r)

    # Calculate total acceleration for the aircraft
    acc = r2dot + w2_x_rdot + wdot_x_r + wxwxr

    # Eotvos correction is the vertical component of the total acceleration of
    # the aircraft - the centrifugal acceleration of the earth, converted to mgal
    E = (acc[3,:] - wexwexr[3,:]) * mps2mgal
    # TODO: Pad the start/end due to loss during derivative computation
    return E

    # Final Return 5-Tuple
    eotvos = (r2dot, w2_x_rdot, wdot_x_r, wxwxr, wexwexr)
    return eotvos
