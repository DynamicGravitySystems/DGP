# coding=utf-8

"""
plots.py
Library for plotting functions

"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.dates as mdates
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import shapely.geometry as sgeom


def read_meterconfig(ini_file, parameter):
    f1 = open(ini_file,"r")
    for line in f1.readlines():
        line_list = line.split('=')
        if line_list[0] == parameter:
            value = float(line_list[1])
    f1.close()
    return value


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
        # for p,v in enumerate(range(number_of_subplots)):
        p = p + 1
        print('{}  {}'.format(p, v))
        ax = plt.subplot(number_of_subplots, 1, p)
        # ax.plot(df.loc[st:et].index, df[v].loc[st:et], color='red', label='ModelOnly',
        # ax.plot(df[v].index, df[v].values, color='red', label='ModelOnly',
        #         ls=my_ls, lw=my_lw, marker=my_marker)
        df[v].plot(ax=ax, color='black', label=v, ls=my_ls, lw=my_lw, marker=my_marker)
        ax.set_title(v)
        ax.set_ylabel(my_varunits[p - 1])

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b %H:%M'))
    fig.autofmt_xdate()
    plt.tight_layout()
    fig.subplots_adjust(top=0.89)
    # ax.legend(ncol=1, loc='upper right')
    # plt.figlegend((ax, ax2), ('ModelOnly', 'Obs'), loc='upper right')#, labelspacing=0.)
    # plt.legend(ncol=1, bbox_to_anchor=(1.1, 1.05))
    plt.savefig(plotname)
    plt.close()


def mapplot_line(pnt_full, pnt, data, var, units='', ptitle='test_map', pfile='test_map'):
    """
    This makes a map plot of line segment
    :param pnt_full:
    :param pnt:
    :param data:
    :param var:
    :param units:
    :param ptitle:
    :param pfile:
    :return:
    """
    try:
        # box = sgeom.box(minx=160, maxx=210, miny=-83, maxy=-77)     # TODO: do this more better
        box = sgeom.box(minx=pnt['long'].min() - 3, maxx=pnt['long'].max() + 3,
                        miny=pnt['lat'].min() - 3, maxy=pnt['lat'].max() + 3)
        x0, y0, x1, y1 = box.bounds
        if x0 < 0:
            myproj = ccrs.SouthPolarStereo(central_longitude=180)
        else:
            myproj = ccrs.NorthPolarStereo(central_longitude=0)
        fig = plt.figure(figsize=(8, 4), facecolor='white', dpi=144)
        ax = plt.axes(projection=myproj)

        s1 = plt.scatter(pnt_full['long'], pnt_full['lat'], c='black', s=1, transform=ccrs.PlateCarree())
        s2 = plt.scatter(pnt['long'], pnt['lat'], c=data[var], cmap=cm.Spectral, s=10, transform=ccrs.PlateCarree())
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
    except IndexError:
        print("Couldn't make Map Plot.")
    return
