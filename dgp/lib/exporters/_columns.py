# -*- coding: utf-8 -*-
from .column_profile import ColumnProfile, Group, Unit

# Standard Column Definitions #
ColumnProfile("gravity", Group.Gravity, "Gravity", unit=Unit.mGal)
ColumnProfile("long_accel", Group.Gravity, unit=Unit.Gal)
ColumnProfile("cross_accel", Group.Gravity, "cross_accel",
              unit=Unit.Gal)
ColumnProfile("beam", Group.Gravity, unit=Unit.Gal)
ColumnProfile("temp", Group.Gravity, "Sensor Temp", unit=Unit.DegC)
ColumnProfile("pressure", Group.Gravity, "Sensor Pressure", unit=Unit.inchHg)
ColumnProfile("Etemp", Group.Gravity, "Electronics Temp", unit=Unit.DegC)
ColumnProfile("latitude", Group.Trajectory, unit=Unit.Degrees)
ColumnProfile("longitude", Group.Trajectory, unit=Unit.Degrees)
ColumnProfile("gps_week", Group.Trajectory)
ColumnProfile("gps_sow", Group.Trajectory)
