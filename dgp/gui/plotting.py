import matplotlib as mpl
mpl.use('Qt5Agg')

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter, num2date
import matplotlib.patches as patches
import numpy as np
import os

class Plots:
    def __init__(self):
        self.rects = []
        self.figure = None
        self.axes = []
        self.clicked = None

    def generate_subplots(self, x, *args):
        def _on_xlims_change(axes):
            # reset the x-axis format when the plot is resized
            axes.get_xaxis().set_major_formatter(DateFormatter('%H:%M:%S'))

        i = 0
        numplots = len(args)
        fig = plt.figure()

        self.cidclick = fig.canvas.mpl_connect('button_press_event', self.onclick)
        self.cidrelease = fig.canvas.mpl_connect('button_release_event', self.onrelease)
        self.cidmotion = fig.canvas.mpl_connect('motion_notify_event', self.onmotion)

        for arg in args:
            if i == 0:
                a = fig.add_subplot(numplots, 1, i+1)
            else:
                a = fig.add_subplot(numplots, 1, i+1, sharex=self.axes[0])

            a.plot(x.to_pydatetime(), arg)
            a.fmt_xdata = DateFormatter('%H:%M:%S')
            a.grid(True)
            a.callbacks.connect('xlim_changed', _on_xlims_change)
            self.axes.append(a)
            i += 1

        if not mpl.is_interactive():
            fig.show()

        self.figure = fig
        plt.show()

    # TO DO: Consider PatchCollection for rectangles.
    def onclick(self, event):
        # TO DO: Don't place rectangle when zooming.
        # TO DO: Resize rectangles when plot extent changes.

        # check if clicked in subplot
        for subplot in self.figure.axes:
            if event.inaxes == subplot:
                break
        else:
            return

        flag = False

        # don't add rectangle if click on existing rectangle
        for partners in self.rects:
        # TO DO: Fix logic in this loop. Don't need to loop through all
        # partners to determine whether click was in an occupied region, just one.
        # Also, use of the flag is a bit kludgy.

            index = 0
            for attr in partners:
                rect = attr['rect']

                # contains, attrd = rect.contains(event)
                # if contains:

                if event.xdata > rect.get_x() and event.xdata < rect.get_x() + rect.get_width():
                    flag = True
                    x0, _ = rect.xy
                    self.clicked = partners, index, x0, event.xdata, event.ydata

                    # draw everything but the selected rectangle and store the pixel buffer
                    canvas = rect.figure.canvas
                    axes = rect.axes
                    rect.set_animated(True)
                    canvas.draw()
                    attr['bg'] = canvas.copy_from_bbox(axes.bbox)

                    # now redraw just the rectangle
                    axes.draw_artist(rect)

                    # and blit just the redrawn area
                    # canvas.blit(axes.bbox)

                index += 1

        if flag:
            return

        # create rectangle if click in empty area
        partners = []
        for subplot in self.figure.axes:
            ylim = subplot.get_ylim()
            xlim = subplot.get_xlim()
            x_extent = (xlim[-1] - xlim[0]) * np.float64(0.1)

            # bottom left corner
            x0 = event.xdata - x_extent/2
            y0 = ylim[0]
            width = x_extent
            height = ylim[-1] - ylim[0]

            r = patches.Rectangle((x0, y0), width, height, alpha=0.1)
            attr = {}
            attr['rect'] = r
            subplot.add_patch(r)

            attr['bg'] = None
            partners.append(attr)

        self.rects.append(partners)
        # self.rect.figure.canvas.draw()
        self.figure.canvas.draw()

    def onmotion(self, event):
        # check if pointer is still in subplot
        for subplot in self.figure.axes:
            if event.inaxes == subplot:
                break
        else:
            return

        if self.clicked is None:
            return
        else:
            self._move_rect(event)

    # def _near_edge(self, event, prox=5):
    #     for partners in self.rects:
    #         attr = partners[0]
    #         left = attr['rect'].get_x()
    #         right = left + attr['rect'].get_width()
    #         if ((event.xdata < left and event.xdata > left - prox) or
    #             (event.xdata > left and event.xdata < left + prox)):
    #             return ("L", partners)
    #         elif ((event.xdata < right and event.xdata > right - prox) or
    #               (event.xdata > right and event.xdata < right + prox)):
    #             return ("R", partners)
    #         else:
    #             return None

    def _move_rect(self, event):
        partners, index, x0, xclick, yclick = self.clicked

        # move rectangles
        dx = event.xdata - xclick
        for attr in partners:
            rect = attr['rect']
            rect.set_x(x0 + dx)
            canvas = rect.figure.canvas
            axes = rect.axes
            canvas.restore_region(attr['bg'])
            axes.draw_artist(rect)
            canvas.blit(axes.bbox)

    def onrelease(self, event):
        for partners in self.rects:
            for attr in partners:
                rect = attr['rect']
                rect.set_animated(False)
                attr['bg'] = None

        self.clicked = None

        # redraw the full figure
        self.figure.canvas.draw()
