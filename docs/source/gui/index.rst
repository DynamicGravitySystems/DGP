dgp.gui package
===============

This package contains modules and sub-packages related to the
Graphical User Interface (GUI) presentation layer of DGP.

DGP's User Interface is built on the Qt 5 C++ library, using the
PyQt Python bindings.

Custom Qt Views, Widgets, and Dialogs are contained here, as well
as plotting interfaces.

Qt Interfaces and Widgets created with Qt Creator generate .ui XML
files, which are then compiled into a Python source files which define
individual UI components.
The .ui source files are contained within the ui directory.

.. seealso::

    `Qt 5 Documentation <http://doc.qt.io>`__

    `PyQt5 Documentation <http://pyqt.sourceforge.net/Docs/PyQt5/>`__


.. toctree::
    :caption: Sub Packages
    :maxdepth: 1

    plotting.rst
