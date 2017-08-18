# coding: utf-8

from collections import namedtuple


"""
Dynamic Gravity Processor (DGP) :: types.py
License: Apache License V2

Overview:
types.py is a library utility module used to define custom reusable types for use in other areas of the project.
"""


location = namedtuple('location', ['lat', 'long', 'alt'])

stillreading = namedtuple('stillreading', ['gravity', 'location', 'time'])
