# -*- coding: utf-8 -*-
from .column_profile import ColumnProfile, Category, Unit

# Standard Column Definitions #
ColumnProfile("gravity", Category.Gravity, "Gravity", unit=Unit.mGal,
              group="AT1")
ColumnProfile("long_accel", Category.Gravity, unit=Unit.Gal, group="AT1")
ColumnProfile("cross_accel", Category.Gravity, "cross_accel",
              unit=Unit.Gal, group="AT1")
ColumnProfile("beam", Category.Gravity, unit=Unit.Gal, group="AT1")
ColumnProfile("temp", Category.Gravity, "Sensor Temp", unit=Unit.DegC,
              group="AT1")
ColumnProfile("pressure", Category.Gravity, "Sensor Pressure", unit=Unit.inchHg,
              group="AT1")
ColumnProfile("Etemp", Category.Gravity, "Electronics Temp", unit=Unit.DegC,
              group="AT1")

ColumnProfile("lat", Category.Trajectory, "Latitude", unit=Unit.Degrees)
ColumnProfile("long", Category.Trajectory, "Longitude", unit=Unit.Degrees)
ColumnProfile("gps_week", Category.Trajectory)
ColumnProfile("gps_sow", Category.Trajectory)

for status_bit in ['clamp', 'unclamp', 'gps_sync', 'feedback', 'reserved1',
                   'reserved2', 'ad_lock', 'cmd_rcvd', 'nav_mode_1',
                   'nav_mode_2', 'plat_comm', 'sens_comm', 'gps_input',
                   'ad_sat', 'long_sat', 'cross_sat', 'on_line']:
    ColumnProfile(status_bit, Category.Status, unit=Unit.Bool, group="AT1")

