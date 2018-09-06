# -*- coding: utf-8 -*-

from .export_profile import ExportProfile

"""Predefined export profiles"""

__all__ = ['standard', 'extended']


standard = ExportProfile(name="Standard",
                         columns=["gravity", "long_accel", "cross_accel",
                                  "beam", "latitude", "longitude"],
                         precision=5, _userprofile=False)

extended = ExportProfile(name="Extended", columns=[], precision=10,
                         _userprofile=False)
