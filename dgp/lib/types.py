# coding: utf-8

from collections import namedtuple

"""
Dynamic Gravity Processor (DGP) :: types.py
License: Apache License V2

Overview:
types.py is a library utility module used to define custom reusable types for use in other areas of the project.
"""


Location = namedtuple('Location', ['lat', 'long', 'alt'])

StillReading = namedtuple('StillReading', ['gravity', 'location', 'time'])

FlightLine = namedtuple('FlightLine', ['id', 'sequence', 'file_ref', 'start', 'end'])

DataCurve = namedtuple('DataCurve', ['channel', 'data'])

DataPacket = namedtuple('DataPacket', ['data', 'path', 'dtype'])
