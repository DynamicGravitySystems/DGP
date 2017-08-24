# coding=utf-8
# based on https://github.com/jrleeman/LongmanTide

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def _calculate_julian_century(timestamp):
    """
    _calculate_julian_century :: datetime-like -> (Integer, Float)

    Computes decimal Julian century and floating point hour with respect to
    12:00 PM, December 31, 1899.

    :param timestamp: datetime to convert
    :return: (integer, float) Decimal Julian century and floating point hour.
    """

    origin_date = datetime(1899, 12, 31, 12, 00, 00)  # Noon Dec 31, 1899
    dt = timestamp - origin_date
    days = dt.days + dt.seconds/3600./24.
    return days/36525, timestamp.hour + timestamp.minute/60. + timestamp.second/3600.

def solve_longman(lat, lon, alt, time):
    """
    solve_longman

    Given the location and datetime object, computes the current
    gravitational tide and associated quantities. Latitude and longitude
    and in the traditional decimal notation, altitude is in meters, time
    is a datetime object.

    :param lat: Latitude in decimal degrees
    :param lon: Longitude in decimal degrees
    :param alt: Altitude above the ellipsoid in meters
    :param time: datetime, datetime index, or datetime series
    :return (float, float, float): Gravity of the sun, moon, and total in mGal.
    """

    T, t0 = _calculate_julian_century(time)

    if isinstance(t0, pd.Index):
        t0 = t0.values

    if isinstance(t0, np.ndarray):
        t0[t0<0] += 24.
        t0[t0>=24] -= 24.
    else:
        if t0 < 0:
            t0 += 24.
        if t0 >= 24:
            t0 -= 24.

    mu = 6.673e-8  # Newton's gravitational constant
    M = 7.3537e25  # Mass of the moon in grams
    S = 1.993e33  # Mass of the sun in grams
    e = 0.05490  # Eccentricity of the moon's orbit
    m = 0.074804  # Ratio of mean motion of the sun to that of the moon
    c = 3.84402e10  # Mean distance between the centers of the earth and the moon
    c1 = 1.495e13  # Mean distance between centers of the earth and sun in cm
    h2 = 0.612  # Love parameter
    k2 = 0.303  # Love parameter
    a = 6.378270e8  # Earth's equitorial radius in cm
    i = 0.08979719  # (i) Inclination of the moon's orbit to the ecliptic
    omega = np.radians(23.452)  # Inclination of the Earth's equator to the ecliptic 23.452 degrees
    L = -1 * lon  # For some reason his lat/lon is defined with W as + and E as -
    lamb = np.radians(lat)  # (lambda) Latitude of point P
    H = alt * 100.  # (H) Altitude above sea-level of point P in cm

    # Lunar Calculations
    # (s) Mean longitude of moon in its orbit reckoned from the referred equinox
    s = 4.72000889397 + 8399.70927456 * T + 3.45575191895e-05 * T * T + 3.49065850399e-08 * T * T * T
    # (p) Mean longitude of lunar perigee
    p = 5.83515162814 + 71.0180412089 * T + 0.000180108282532 * T * T + 1.74532925199e-07 * T * T * T
    # (h) Mean longitude of the sun
    h = 4.88162798259 + 628.331950894 * T + 5.23598775598e-06 * T * T
    # (N) Longitude of the moon's ascending node in its orbit reckoned from the referred equinox
    N = 4.52360161181 - 33.757146295 * T + 3.6264063347e-05 * T * T +  3.39369576777e-08 * T * T * T
    # (I) Inclination of the moon's orbit to the equator
    I = np.arccos(np.cos(omega) * np.cos(i) - np.sin(omega) * np.sin(i) * np.cos(N))
    # (nu) Longitude in the celestial equator of its intersection A with the moon's orbit
    nu = np.arcsin(np.sin(i) * np.sin(N) / np.sin(I))
    # (t) Hour angle of mean sun measured west-ward from the place of observations
    t = np.radians(15. * (t0 - 12) - L)

    # (chi) right ascension of meridian of place of observations reckoned from A
    chi = t + h - nu
    # cos(alpha) where alpha is defined in eq. 15 and 16
    cos_alpha = np.cos(N) * np.cos(nu) + np.sin(N) * np.sin(nu) * np.cos(omega)
    # sin(alpha) where alpha is defined in eq. 15 and 16
    sin_alpha = np.sin(omega) * np.sin(N) / np.sin(I)
    # (alpha) alpha is defined in eq. 15 and 16
    alpha = 2 * np.arctan(sin_alpha / (1 + cos_alpha))
    # (xi) Longitude in the moon's orbit of its ascending intersection with the celestial equator
    xi = N - alpha

    # (sigma) Mean longitude of moon in radians in its orbit reckoned from A
    sigma = s - xi
    # (l) Longitude of moon in its orbit reckoned from its ascending intersection with the equator
    l = (sigma + 2 * e * np.sin(s - p) + (5. / 4) * e * e * np.sin(2 * (s - p))
         + (15./4) * m * e * np.sin(s - 2 * h + p) + (11. / 8) * m * m * np.sin(2 * (s - h)))

    # Sun
    # (p1) Mean longitude of solar perigee
    p1 = (4.90822941839 + 0.0300025492114 * T +  7.85398163397e-06 * T
          * T + 5.3329504922e-08 * T * T * T)
    # (e1) Eccentricity of the Earth's orbit
    e1 = 0.01675104-0.00004180 * T - 0.000000126 * T * T
    # (chi1) right ascension of meridian of place of observations reckoned from the vernal equinox
    chi1 = t + h
    # (l1) Longitude of sun in the ecliptic reckoned from the vernal equinox
    l1 = h + 2 * e1 * np.sin(h - p1)
    # cosine(theta) Theta represents the zenith angle of the moon
    cos_theta = (np.sin(lamb) * np.sin(I) * np.sin(l)
                 + np.cos(lamb) * (np.cos(0.5 * I) ** 2 * np.cos(l - chi)
                 + np.sin(0.5 * I) ** 2 * np.cos(l + chi)))
    # cosine(phi) Phi represents the zenith angle of the run
    cos_phi = (np.sin(lamb) * np.sin(omega) * np.sin(l1)
               + np.cos(lamb) * (np.cos(0.5 * omega) ** 2
                               * np.cos(l1 - chi1)
                               + np.sin(0.5 * omega) ** 2 * np.cos(l1 + chi1)))

    # Distance
    # (C) Distance parameter, equation 34
    C = np.sqrt(1. / (1 + 0.006738 * np.sin(lamb) ** 2))
    # (r) Distance from point P to the center of the Earth
    r = C * a + H
    # (a') Distance parameter, equation 31
    aprime = 1. / (c * (1 - e * e))
    # (a1') Distance parameter, equation 31
    aprime1 = 1. / (c1 * (1 - e1 * e1))
    # (d) Distance between centers of the Earth and the moon
    d = (1. / ((1. / c) + aprime * e * np.cos(s - p) + aprime * e * e * np.cos(2 * (s - p))
         + (15./8) * aprime * m * e * np.cos(s - 2 * h + p)
         + aprime * m * m * np.cos(2 * (s - h))))
    # (D) Distance between centers of the Earth and the sun
    D = 1. / ((1. / c1) + aprime1 * e1 * np.cos(h - p1))

    # (gm) Vertical componet of tidal acceleration due to the moon
    gm = ((mu * M * r / (d * d * d)) * (3 * cos_theta ** 2 - 1)
          + (3. / 2) * (mu * M * r * r / (d * d * d * d)) * (5 * cos_theta ** 3 - 3 * cos_theta))
    # (gs) Vertical componet of tidal acceleration due to the sun
    gs = mu * S * r / (D * D * D) * (3 * cos_phi ** 2 - 1)

    love = (1 + h2 - 1.5 * k2)
    g0 = (gm + gs) * 1e3 * love
    return gm * 1e3 * love, gs * 1e3 * love, g0
