# -*- coding: utf-8 -*-
from .column_profile import ColumnProfile, Category, Unit

# Standard Column Definitions #
ColumnProfile("gravity", Category.Gravity, "Gravity", unit=Unit.mGal)
ColumnProfile("long_accel", Category.Gravity, unit=Unit.Gal)
ColumnProfile("cross_accel", Category.Gravity, "cross_accel",
              unit=Unit.Gal)
ColumnProfile("beam", Category.Gravity, unit=Unit.Gal)
ColumnProfile("temp", Category.Gravity, "Sensor Temp", unit=Unit.DegC)
ColumnProfile("pressure", Category.Gravity, "Sensor Pressure", unit=Unit.inchHg)
ColumnProfile("Etemp", Category.Gravity, "Electronics Temp", unit=Unit.DegC)
ColumnProfile("lat", Category.Trajectory, "Latitude", unit=Unit.Degrees)
ColumnProfile("long", Category.Trajectory, "Longitude", unit=Unit.Degrees)
ColumnProfile("gps_week", Category.Trajectory)
ColumnProfile("gps_sow", Category.Trajectory)
