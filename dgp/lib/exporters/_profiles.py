# -*- coding: utf-8 -*-

from .export_profile import BuiltinExportProfile

"""Predefined export profiles"""

__all__ = ['standard', 'extended']

standard = BuiltinExportProfile(name="Standard", precision=5,
                                columns=["gravity", "long_accel", "cross_accel",
                                         "beam", "lat", "long"],
                                description="Standard profile contains "
                                            "abbreviated selection of gravity "
                                            "and trajectory columns."
                                )

extended = BuiltinExportProfile(name="Extended", precision=10,
                                columns=["gravity", "long_accel", "cross_accel",
                                         "beam", "temp", "pressure", "Etemp",
                                         "lat", "long", "gps_week", "gps_sow"],
                                description="Extended profile contains all common raw data columns.")
