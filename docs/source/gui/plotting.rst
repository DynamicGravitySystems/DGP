dgp.gui.plotting package
========================

The plotting package contains the backend wrappers and classes used by the DGP
application to interactively plot data within the GUI.

The interactive plotting framework that we utilize here is based on the
`PyQtGraph <http://http://pyqtgraph.org/documentation/index.html>`__  python
package, which itself utilizes the
`Qt Graphics View Framework <http://doc.qt.io/qt-5/graphicsview.html>`__ to
provide a highly performant interactive plotting interface.


The modules within the plotting package are separated into the :ref:`bases`,
:ref:`plotters` and :ref:`helpers` modules, which provide the base plot
wrappers, task/application specific plot widgets, and plot utility functions/
classes respectively.

The :ref:`bases` module defines the base plot wrappers which wrap some of
PyQtGraph's plotting functionality to ease the plotting and management of
Pandas Series data within a plot surface.

The :ref:`plotters` module provides task specific plot widgets that can be
directly incorporated into a QtWidget application's layout. These classes add
specific functionality to the base 'backend' plots, for example to enable
graphical click-drag selection of data segments by the user.



.. py:module:: dgp.gui.plotting

.. _bases:

Bases
-----

.. autoclass:: dgp.gui.plotting.backends.GridPlotWidget
    :undoc-members:
    :show-inheritance:

.. autoclass:: dgp.gui.plotting.backends.LinkedPlotItem
    :show-inheritance:

.. _plotters:

Plotters
--------

.. autoclass:: dgp.gui.plotting.plotters.LineSelectPlot
    :undoc-members:
    :show-inheritance:

.. _helpers:

Helpers
-------

.. autoclass:: dgp.gui.plotting.helpers.PolyAxis
    :undoc-members:
    :show-inheritance:

.. autoclass:: dgp.gui.plotting.helpers.LinearSegment
    :undoc-members:
    :show-inheritance:
