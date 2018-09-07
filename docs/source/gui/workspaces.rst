dgp.gui.workspaces package
==========================


The Workspaces sub-package defines GUI widgets for various controller
contexts in the DGP application.
The idea being that there are naturally different standard ways in which the
user will interact with different project objects/controllers, depending on the
type of the object.

The workspaces are intended to be displayed within a QTabWidget within the
application so that the user may easily navigate between multiple open
workspaces.

Each workspace defines its own custom widget(s) for interacting & manipulating
data associated with its underlying controller (:class:`AbstractController`).

Workspaces may also contain sub-tabs, for example the :class:`DataSetTab`
defines sub-tabs for viewing raw-data and selecting segments, and a tab for
executing transform graphs on the data.

.. contents::
    :depth: 3


Base Interfaces
---------------

.. versionadded:: 0.1.0

.. automodule:: dgp.gui.workspaces.base


Workspaces
----------

Project Workspace
^^^^^^^^^^^^^^^^^

.. warning:: Not yet implemented

.. note::

    Future Planning: Project Workspace may display a map interface which can
    overlay each flight's trajectory path from the flights within the project.
    Some interface to allow comparison of flight data may also be integrated into
    this workspace.

.. automodule:: dgp.gui.workspaces.project

Flight Workspace
^^^^^^^^^^^^^^^^
.. warning:: Not yet implemented

.. note::

    Future Planning: Similar to the project workspace, the flight workspace may
    be used to display a map of the selected flight.
    A dashboard type widget may be implemented to show details of the flight,
    and to allow users to view/configure flight specific parameters.

.. automodule:: dgp.gui.workspaces.flight


DataSet Workspace
^^^^^^^^^^^^^^^^^
.. versionadded:: 0.1.0

.. automodule:: dgp.gui.workspaces.dataset



DataFile Workspace
^^^^^^^^^^^^^^^^^^
.. warning:: Not yet implemented

.. note::

    Future Planning: The DataFile workspace may be used to allow users to view
    and possibly edit raw data within the interface in a spreadsheet style
    view/control.

