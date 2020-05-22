import os
from datetime import datetime
import yaml
import sys

from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.trajectory_ingestor import import_trajectory, import_imar_zbias
from dgp.lib.etc import align_frames
from dgp.lib.transform.transform_graphs import AirbornePost
from dgp.lib.transform.filters import detrend
from dgp.lib.plots import timeseries_gravity_diagnostic, mapplot_segment, read_meterconfig

# Runtime Options
write_out = True
make_plots = True
add_map_plots = False
diagnostic = True
import_auxiliary = True

# Confirm a few things with the human
if diagnostic:
    print("Diagnostic set to True. The means:\n"
          "1) entire gravity record used,\n"
          "2) still readings NOT considered (no detrend)\n")

# Read YAML config file
try:
    config_file = sys.argv[1]
    print(f"Getting processing parameters from {config_file}")
except IndexError:
    proj_path = os.path.abspath(os.path.dirname(__file__))
    config_file = os.path.join(proj_path, 'config_runtime.yaml')
    print(f"Reading default configuration file from {proj_path}")

with open(config_file, 'r') as file:  #  TODO write a functino to get parameters from conig YAML all at once
    config = yaml.safe_load(file)
print(f"\n~~~~~~~~~~~ Flight {config['flight']} ~~~~~~~~~~~")
campaign = config['campaign']
flight = config['flight']
gravity_directory = config['gravity_dir']
gravity_file = config['gravity_file']
trajectory_source = config['trajectory_src']
trajectory_directory = config['trajectory_dir']
trajectory_file = config['trajectory_file']
gps_fields = config['gps_fields']
meterconfig_dir = config['config_dir']
outdir = config['out_dir']
try:
    QC_segment = config['QC1']  #
    QC_plot = True
except KeyError:
    print('No QC Segments...')
    QC_plot = False
if trajectory_source == 'Waypoint':
    trajectory_engine = 'c'
    trajectory_delim = ','
else:
    trajectory_engine = 'python'
    trajectory_delim = '\s+'

# Load Data Files
print('\nImporting gravity')
gravity = read_at1a(os.path.join(gravity_directory, gravity_file), interp=True)
print(f"Gravity Data Starts: {gravity.index[0]}")
print(f"Gravity Data Ends: {gravity.index[-1]}")
print('\nImporting trajectory')
trajectory = import_trajectory(os.path.join(trajectory_directory, trajectory_file),
                               columns=gps_fields, skiprows=1,
                               timeformat='hms', engine=trajectory_engine, sep=trajectory_delim)
# Append iMAR AccBiasZ
if import_auxiliary:
    plot_imar = True
    imar_file = trajectory_file.replace('DGS', 'iMAR_1Hz')
    # imar_file = f'{os.path.splitext(imar_file)[0]}_1Hz{os.path.splitext(imar_file)[1]}'
    imar = import_imar_zbias(os.path.join(trajectory_directory, imar_file))
    # imar_10Hz = imar.resample('100L').first().bfill(limit=1)[['lat','z_acc_bias']].interpolate(method='linear', limit_area='inside')

    import pandas as pd
    # pd.merge(gravity, imar_10Hz).head()
    gravity = pd.concat([gravity, imar[['z_acc_bias']]], axis=1)
    gravity['z_acc_bias'] = gravity[['z_acc_bias']].interpolate(method='linear', limit_area='inside')


# Read MeterProcessing file in Data Directory
meterconfig_file = os.path.join(meterconfig_dir, 'DGS_config_files', 'MeterProcessing.ini')
if diagnostic:
    k_factor = 1
else:
    k_factor = read_meterconfig(meterconfig_file, 'kfactor')
tie_gravity = read_meterconfig(meterconfig_file, 'TieGravity')
if abs(tie_gravity / 980000) > 2:
    print("Check your gravity tie units.")
    exit()

print(f"K-factor:    {k_factor}\nGravity-tie: {tie_gravity}\n")

# Still Readings
#  TODO: Semi-automate or create GUI to get statics
first_static = read_meterconfig(meterconfig_file, 'PreStill')
second_static = read_meterconfig(meterconfig_file, 'PostStill')

# pre-processing prep
if diagnostic:
    begin_line = gravity.index[0]
    end_line = gravity.index[-1]
else:
    begin_line = datetime.strptime(config['begin_line'], '%Y-%m-%d %H:%M')
    end_line = datetime.strptime(config['end_line'], '%Y-%m-%d %H:%M')
    if not begin_line < end_line:
        print("Check your times.  Using start and end of gravity file instead.")
        begin_line = gravity.index[0]
        end_line = gravity.index[-1]


if add_map_plots:
    trajectory_full = trajectory[['long', 'lat']]
gravity = gravity[(begin_line <= gravity.index) & (gravity.index <= end_line)]
trajectory = trajectory[(begin_line <= trajectory.index) & (trajectory.index <= end_line)]

# Save a 'meter_gravity' column for diagnostic output
gravity['meter_gravity'] = gravity['gravity']

# align gravity and trajectory frames
gravity, trajectory = align_frames(gravity, trajectory)

# Check that arrays are same length
if abs(gravity.shape[0] - trajectory.shape[0]) > 0:
    trajectory = trajectory.iloc[0:gravity.shape[0]]
    # TODO or check for duplicates, like trajectory.drop_duplicates(keep='first')

# adjust for crossing the prime meridian
trajectory['long'] = trajectory['long'].where(trajectory['long'] > 0, trajectory['long'] + 360)

# de-drift
if not diagnostic:
    gravity['gravity'] = detrend(gravity['gravity'], first_static, second_static)

# adjust to absolute
offset = tie_gravity - k_factor * first_static
gravity['gravity'] += offset

print('\nProcessing')
g = AirbornePost(trajectory, gravity, begin_static=first_static, end_static=second_static)
results = g.execute()

# Check that arrays are same length
if abs(gravity.shape[0] - results['corrected_grav'].shape[0]) != 0:
    results['corrected_grav'] = results['corrected_grav'].iloc[0:gravity.shape[0]]
if abs(gravity.shape[0] - results['filtered_grav'].shape[0]) != 0:
    results['filtered_grav'] = results['filtered_grav'].iloc[0:gravity.shape[0]]

# TODO: split this file up into a QC and Official output
if write_out:
    import numpy as np
    import pandas as pd

    print('\nWriting Output to File')
    time = pd.Series(trajectory.index.astype(np.int64) / 10 ** 9,
                     index=trajectory.index, name='unix_time')
    columns = ['unixtime', 'lat', 'long', 'ell_ht',
               'eotvos_corr', 'kin_accel_corr',
               'meter_grav', 'beam',
               'lat_corr', 'fa_corr', 'total_corr',
               'abs_grav', 'FAA', 'FAA_LP']
    out_array = np.array([time.values,
                       trajectory['lat'].values.round(decimals=6),
                       trajectory['long'].values.round(decimals=6),
                       trajectory['ell_ht'].values.round(decimals=3),
                       results['eotvos'].values.round(decimals=2),
                       results['kin_accel'].values.round(decimals=2),
                       gravity['meter_gravity'].values.round(decimals=2),
                       gravity['beam'].values.round(decimals=5),
                       results['lat_corr'].values.round(decimals=2),
                       results['fac'].values.round(decimals=2),
                       results['total_corr'].values.round(decimals=2),
                       results['abs_grav'].values.round(decimals=2),
                       results['corrected_grav'].values.round(decimals=2),
                       results['filtered_grav'].values.round(decimals=2)])
    if import_auxiliary:
        columns += ['AccBiasZ']
        out_array = np.vstack([out_array, gravity['z_acc_bias'].values.round(decimals=7)])
    df = pd.DataFrame(data=out_array.T, columns=columns, index=time)
    df = df.apply(pd.to_numeric, errors='ignore')
    df.index = pd.to_datetime(trajectory.index)
    outfile = os.path.join(outdir,
                           '{}_{}_{}_DGS_FINAL.csv'.format(campaign, flight, str(begin_line.strftime('%Y%m%d_%H%Mz'))))
    df.to_csv(outfile)  # , na_rep=" ")

###########
# Real plots

if make_plots:
    print('\nPlotting')
    # Time-series Plot
    variables = ['meter_gravity', 'gravity', 'cross_accel', 'beam', 'temp']
    variable_units = ['mGal', 'mGal', 'mGal', ' ', 'C']
    plot_title = '{} {}: QC'.format(campaign, flight)
    plot_file = os.path.join(outdir, '{}_{}_DGP_QCplot_meter.png'.format(campaign, flight))
    timeseries_gravity_diagnostic(gravity, variables, variable_units, begin_line, end_line,
                                  plot_title, plot_file)

    variables = ['ell_ht', 'lat', 'long']
    variable_units = ['m', 'degrees', 'degrees']
    plot_title = '{} {}: PNT'.format(campaign, flight)
    plot_file = os.path.join(outdir, '{}_{}_DGP_QCplot_trajectory.png'.format(campaign, flight))
    timeseries_gravity_diagnostic(results['trajectory'], variables, variable_units, begin_line, end_line,
                                  plot_title, plot_file)

    variables = ['eotvos', 'lat_corr', 'fac', 'kin_accel', 'total_corr']
    variable_units = ['mGal', 'mGal', 'mGal', 'mGal', 'mGal']
    plot_title = '{} {}: Corrections'.format(campaign, flight)
    plot_file = os.path.join(outdir, '{}_{}_DGP_QCplot_corrections.png'.format(campaign, flight))
    timeseries_gravity_diagnostic(results, variables, variable_units, begin_line, end_line,
                                  plot_title, plot_file)

    variables = ['abs_grav', 'corrected_grav', 'filtered_grav']
    variable_units = ['mGal', 'mGal', 'mGal']
    plot_title = '{} {}: Gravity'.format(campaign, flight)
    plot_file = os.path.join(outdir, '{}_{}_DGP_QCplot_freeair.png'.format(campaign, flight))
    timeseries_gravity_diagnostic(results, variables, variable_units, begin_line, end_line,
                                  plot_title, plot_file)

    if QC_plot:
        # QC Segment Plot - AccBiasZ
        try:
            variables = ['z_acc_bias', 'long_accel', 'cross_accel']
            variable_units = ['mGal', 'mGal', 'mGal', 'mGal']
            plot_title = '{} {}: Accel (segment)'.format(campaign, flight)
            plot_file = os.path.join(outdir, '{}_{}_DGP_QCplot_accel_segment.png'.format(campaign, flight))
            timeseries_gravity_diagnostic(gravity, variables, variable_units,
                                          QC_segment['start'], QC_segment['end'],
                                          plot_title, plot_file)
        except KeyError:
            print("Couldn't make AccBiasZ plot...")
        # QC Segment Plot - Gravity Output
        variables = ['filtered_grav', 'corrected_grav', 'abs_grav']
        variable_units = ['mGal', 'mGal', 'mGal', 'mGal']
        plot_title = '{} {}: Gravity (segment)'.format(campaign, flight)
        plot_file = os.path.join(outdir, '{}_{}_DGP_QCplot_freeair_segment.png'.format(campaign, flight))
        timeseries_gravity_diagnostic(results, variables, variable_units,
                                      QC_segment['start'], QC_segment['end'],
                                      plot_title, plot_file)

    if add_map_plots:
        plot_title = '{} {}: Gravity'.format(campaign, flight)
        plot_file = os.path.join(outdir, '{}_{}_DGP_QCplot_freeair_map.png'.format(campaign, flight))
        mapplot_segment(results, 'filtered_grav',
                        QC_segment['start'], QC_segment['end'],
                        'mGal', plot_title, plot_file)
