import os
from datetime import datetime

from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.trajectory_ingestor import import_trajectory
from dgp.lib.etc import align_frames
from dgp.lib.transform.transform_graphs import AirbornePost
from dgp.lib.transform.filters import detrend
from dgp.lib.plots import timeseries_gravity_diagnostic, mapplot_line, read_meterconfig

# Runtime Option
campaign = 'OIB'    # 'ROSETTA'

# Set paths
if campaign == 'ROSETTA':
    print('ROSETTA')
    basedir = '/Users/dporter/Documents/Research/Projects/DGP_test/'
    gravity_directory = 'DGP_data'
    gravity_file = 'AN04_F1001_20171103_2127.dat'
    trajectory_directory = gravity_directory
    trajectory_file = 'AN04_F1001_20171103_DGS-INS_FINAL_DGS.txt'
    # L650
    begin_line = datetime(2017, 11, 4, 0, 27)
    end_line = datetime(2017, 11, 4, 1, 45)
    gps_fields = ['mdy', 'hms', 'lat', 'long', 'ortho_ht', 'ell_ht', 'num_stats', 'pdop']
elif campaign == 'OIB':
    print('OIB')
    basedir = '/Users/dporter/Documents/Research/Projects/OIB-grav/data/P3_2017'
    gravity_directory = 'gravity/dgs/raw/F2004'
    gravity_file = 'OIB-P3_20170327_F2004_DGS_0938.dat'
    trajectory_directory = 'pnt/dgs-ins/F2004/txt'
    trajectory_file = 'OIB-P3_20170327_F2004_DGS-INS_RAPID_DGS.txt'
    # NW Coast Parallel
    begin_line = datetime(2017, 3, 27, 15, 35)
    end_line = datetime(2017, 3, 27, 16, 50)
    gps_fields = ['mdy', 'hms', 'lat', 'long', 'ortho_ht', 'ell_ht', 'num_stats', 'pdop']

else:
    print('Scotia?')

# Load Data Files
print('\nImporting gravity')
gravity = read_at1a(os.path.join(basedir, gravity_directory, gravity_file), interp=True)
print('\nImporting trajectory')
trajectory = import_trajectory(os.path.join(basedir, trajectory_directory, trajectory_file),
                               columns=gps_fields, skiprows=1, timeformat='hms')

# Read MeterProcessing file in Data Directory
config_file = os.path.join(basedir, gravity_directory, "MeterProcessing.ini")
k_factor = read_meterconfig(config_file, 'kfactor')
tie_gravity = read_meterconfig(config_file, 'TieGravity')
print('{0} {1}'.format(k_factor, tie_gravity))
flight = gravity_file[4:11]

# statics
#  TODO: Semi-automate or create GUI to get statics
first_static = read_meterconfig(config_file, 'PreStill')
second_static = read_meterconfig(config_file, 'PostStill')
# def compute_static(begin, end):
#     return gravity[(begin < gravity.index) & (gravity.index < end)]['gravity'].mean()
#
# begin_first_static = datetime(2016, 8, 10, 19, 57)
# end_first_static = datetime(2016, 8, 10, 20, 8)
# first_static = compute_static(begin_first_static, end_first_static)
#
# begin_second_static = datetime(2016, 8, 10, 21, 7)
# end_second_static = datetime(2016, 8, 10, 21, 17)
# second_static = compute_static(begin_second_static, end_second_static)

# pre-processing prep
trajectory_full = trajectory[['long', 'lat']]
gravity = gravity[(begin_line <= gravity.index) & (gravity.index <= end_line)]
trajectory = trajectory[(begin_line <= trajectory.index) & (trajectory.index <= end_line)]

# align gravity and trajectory frames
gravity, trajectory = align_frames(gravity, trajectory)

# adjust for crossing the prime meridian
trajectory['long'] = trajectory['long'].where(trajectory['long'] > 0, trajectory['long'] + 360)

# de-drift
gravity['gravity'] = detrend(gravity['gravity'], first_static, second_static)

# adjust to absolute
offset = tie_gravity - k_factor * first_static
gravity['gravity'] += offset

# print('\nProcessing')
# g = AirbornePost(trajectory, gravity, begin_static=first_static, end_static=second_static)
# results = g.execute()

###########
# Real plots
print('\nPlotting')
if 'results' in locals():
    # Time-series Plot
    variables = ['ell_ht', 'lat', 'long']
    variable_units = ['m', 'degrees', 'degrees']
    plot_title = campaign + ' ' + flight + ': PNT'
    plot_name = os.path.join(basedir, campaign + '_' + flight + '_DGP_TS_pnt.png')
    timeseries_gravity_diagnostic(results['shifted_trajectory'], variables, variable_units, begin_line, end_line,
                                  plot_title, plot_name)

    # Time-series Plot
    variables = ['eotvos', 'lat_corr', 'fac', 'total_corr']
    variable_units = ['mGal', 'mGal', 'mGal', 'mGal']
    plot_title = campaign + ' ' + flight + ': Corrections'
    plot_name = os.path.join(basedir, campaign + '_' + flight + '_DGP_TS_corrections.png')
    timeseries_gravity_diagnostic(results, variables, variable_units, begin_line, end_line,
                                  plot_title, plot_name)

    # Time-series Plot
    variables = ['filtered_grav', 'corrected_grav', 'abs_grav']
    variable_units = ['mGal', 'mGal', 'mGal', 'mGal']
    plot_title = campaign + ' ' + flight + ': Gravity'
    plot_name = os.path.join(basedir, campaign + '_' + flight + '_DGP_TS_gravity.png')
    timeseries_gravity_diagnostic(results, variables, variable_units, begin_line, end_line,
                                  plot_title, plot_name)

    # Map Plot
    plot_title = campaign + ' ' + flight + ': Gravity'
    plot_name = os.path.join(basedir, campaign + '_' + flight + '_DGP_mapplot_gravity.png')
    mapplot_line(trajectory_full, trajectory, results, 'filtered_grav', 'mGal', plot_title, plot_name)
else:
    # Temporary plots for when graph is commented out (currently OIB_P3)
    variables = ['gravity', 'cross_accel', 'beam', 'temp']
    variable_units = ['mGal', 'mGal', 'mGal', 'C']
    plot_title = campaign + ' ' + flight + ': QC'
    plot_name = os.path.join(basedir, campaign + '_' + flight + '_DGP_TS_QC.png')
    timeseries_gravity_diagnostic(gravity, variables, variable_units, begin_line, end_line,
                                  plot_title, plot_name)

    variables = ['ell_ht', 'ortho_ht', 'lat', 'long']
    variable_units = ['m', 'm', 'degrees', 'degrees']
    plot_title = campaign + ' ' + flight + ': PNT'
    plot_name = os.path.join(basedir, campaign + '_' + flight + '_DGP_TS_pnt.png')
    timeseries_gravity_diagnostic(trajectory, variables, variable_units, begin_line, end_line,
                                  plot_title, plot_name)

    plot_title = campaign + ' ' + flight + ': Gravity'
    plot_name = os.path.join(basedir, campaign + '_' + flight + '_DGP_mapplot_gravity.png')
    mapplot_line(trajectory_full, trajectory, gravity, 'gravity', 'mGal', plot_title, plot_name)
