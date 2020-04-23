# coding=utf-8

"""
plots.py
Library for plotting functions

"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.dates as mdates


def read_meterconfig(ini_file, parameter):
    f1 = open(ini_file,"r")
    for line in f1.readlines():
        line_list = line.split('=')
        if line_list[0] == parameter:
            value = float(line_list[1])
    f1.close()
    return value


def compute_static_mean(df, begin, end):
    return df[(begin < df.index) & (df.index < end)]['gravity'].mean()


def timeseries_gravity_diagnostic(df, my_varlist, my_varunits, st, et, plottitle, plotname, **kwargs):
    """
    Plots any number of varaibles in a single dataframe, but please adjust the figure size
    until I figure out how to do it more better.
    Parameters
    ----------
    df : pandas.DataFrame
        Base DataFrame
    my_varlist : list
                variables to be plotted (must be same as DataFrame columns)
    my_varunits : list
                variable units
    st : datetime
        start time
    et : datetime
        end time
    plottitle : string
    plotname : string


    Returns
    -------
    plot : plt.figure
        Multi-paneled Timeseries Figure
    """

    my_ls = '-'
    my_lw = 0.5
    my_marker = None
    print('p  v')
    plt.subplots_adjust(hspace=0.000)
    plt.style.use('ggplot')
    number_of_subplots = np.shape(my_varlist)[0]
    fig = plt.figure(figsize=(8, 6), facecolor='white', dpi=96)
    fig.suptitle(plottitle)
    for p, v in enumerate(my_varlist):
        p = p + 1
        print('{}  {}'.format(p, v))
        ax = plt.subplot(number_of_subplots, 1, p)
        ax.plot(df[v].loc[st:et].index, df[v].loc[st:et].values, color='black', label=v,
                ls=my_ls, lw=my_lw, marker=my_marker)
        ax.set_title(v)
        ax.set_ylabel(my_varunits[p - 1])

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b %H:%M'))
    fig.autofmt_xdate()
    plt.tight_layout()
    fig.subplots_adjust(top=0.89)
    plt.savefig(plotname)
    plt.close()


def mapplot_line(pnt_full, pnt, data, var, begin_segment, end_segment, units='', ptitle='test_map', pfile='test_map'):
    """
    This makes a map plot of the full line
    :param pnt_full:
    :param pnt:
    :param data:
    :param var:
    :param units:
    :param ptitle:
    :param pfile:
    :return:
    """
    import cartopy.crs as ccrs
    from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
    import shapely.geometry as sgeom

    data = data[var][(begin_segment <= data[var].index) & (data[var].index <= end_segment)]
    box = sgeom.box(minx=pnt['long'].min() - 2, maxx=pnt['long'].max() + 2,
                    miny=pnt['lat'].min() - 2, maxy=pnt['lat'].max() + 2)
    x0, y0, x1, y1 = box.bounds
    if x0 < 0:
        myproj = ccrs.SouthPolarStereo(central_longitude=180)
    else:
        myproj = ccrs.NorthPolarStereo(central_longitude=0)
    fig = plt.figure(figsize=(8, 4), facecolor='white', dpi=144)
    ax = plt.axes(projection=myproj)

    s1 = plt.scatter(pnt_full['long'], pnt_full['lat'], c='black', s=1, transform=ccrs.PlateCarree())
    s2 = plt.scatter(pnt['long'], pnt['lat'], c=data, cmap=cm.Spectral, s=10, transform=ccrs.PlateCarree())
    p1 = ax.plot(pnt['long'][0], pnt['lat'][0], 'k*', markersize=7, transform=ccrs.PlateCarree())
    cb = fig.colorbar(s2, ax=ax, label=units,
                      orientation='vertical', shrink=0.8, pad=0.05)
    cb.ax.set_yticklabels(cb.ax.get_yticklabels(), rotation=0)
    cb.ax.tick_params(labelsize=6)

    ax.coastlines(resolution='10m')
    ax.xlabels_top = ax.ylabels_right = False
    ax.gridlines(draw_labels=False, alpha=0.3, color='grey')
    ax.xformatter = LONGITUDE_FORMATTER
    ax.yformatter = LATITUDE_FORMATTER
    ax.set_extent([x0, x1, y0, y1], ccrs.PlateCarree())

    plt.tight_layout()
    plt.subplots_adjust(top=0.90)
    plt.suptitle(ptitle, y=0.98)
    plt.savefig(pfile, bbox_inches='tight')  # save the figure to file
    plt.close()


def mapplot_segment(df, var, begin_segment, end_segment, units='', ptitle='test_map', pfile='test_map'):
    """
    This makes a map plot of line segment
    :param df:
    :param var:
    :param begin_segment:
    :param end_segment:
    :param units:
    :param ptitle:
    :param pfile:
    :return:
    """
    import cartopy.crs as ccrs
    from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
    import shapely.geometry as sgeom

    data = df[var][(begin_segment <= df[var].index) & (df[var].index <= end_segment)]
    lat = df['trajectory'].lat[(begin_segment <= df['trajectory'].lat.index)
                               & (df['trajectory'].lat.index <= end_segment)]
    long = df['trajectory'].long[(begin_segment <= df['trajectory'].long.index)
                                 & (df['trajectory'].long.index <= end_segment)]
    box = sgeom.box(minx=long.min() - 1, maxx=long.max() + 1,
                    miny=lat.min() - 1, maxy=lat.max() + 1)
    x0, y0, x1, y1 = box.bounds
    if x0 < 0:
        myproj = ccrs.SouthPolarStereo(central_longitude=180)
    else:
        myproj = ccrs.NorthPolarStereo(central_longitude=0)
    fig = plt.figure(figsize=(8, 4), facecolor='white', dpi=144)
    ax = plt.axes(projection=myproj)

    s2 = plt.scatter(long, lat, c=data, cmap=cm.Spectral, s=10, transform=ccrs.PlateCarree())
    cb = fig.colorbar(s2, ax=ax, label=units,
                      orientation='vertical', shrink=0.8, pad=0.05)
    cb.ax.set_yticklabels(cb.ax.get_yticklabels(), rotation=0)
    cb.ax.tick_params(labelsize=6)

    ax.coastlines(resolution='10m')
    ax.xlabels_top = ax.ylabels_right = False
    ax.gridlines(draw_labels=False, alpha=0.3, color='grey')
    ax.xformatter = LONGITUDE_FORMATTER
    ax.yformatter = LATITUDE_FORMATTER
    # ax.set_extent([x0, x1, y0, y1], ccrs.PlateCarree())

    plt.tight_layout()
    plt.subplots_adjust(top=0.90)
    plt.suptitle(ptitle, y=0.98)
    plt.savefig(pfile, bbox_inches='tight')  # save the figure to file
    plt.close()
