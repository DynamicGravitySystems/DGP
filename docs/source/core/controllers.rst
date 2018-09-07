dgp.core.controllers package
============================

The Controllers package contains the various controller classes which are
layered on top of the core 'data models' (see the :doc:`models`) which
themselves store the raw project data.

The function of the controller classes is to provide an interaction
layer on top of the data layer - without complicating the underlying
data classes, especially as the data classes must undergo serialization
and de-serialization.

The controllers provide various functionality related to creating,
traversing, and mutating the project tree-hierarchy. The controllers
also interact in minor ways with the UI, and more importantly, are the
layer by which the UI interacts with the underlying project data.


TODO: Add Controller Hierarchy like in models.rst


Controller Development Principles
---------------------------------

.. py:currentmodule:: dgp.core.controllers

Controllers typically should match 1:1 a model class, though there are cases
for creating controllers such as the :class:`~.project_containers.ProjectFolder`
which is a utility class for grouping items visually in the project's tree view.

Controllers should at minimum subclass
:class:`~.controller_interfaces.AbstractController` which configures inheritance
for :class:`QStandardItem` and :class:`~.controller_mixins.AttributeProxy`.
For more complex and widely used controllers, a dedicated interface should be
created following the same naming scheme - particularly where circular
dependencies may be introduced.


Context Menu Declarations
^^^^^^^^^^^^^^^^^^^^^^^^^

Due to the nature of :class:`QMenu`, the menu cannot be instantiated directly
ahead of time as it requires a parent :class:`QWidget` to bind to. This has
led to the current solution which lets each controller declaratively define
their context menu items and actions (with some common actions mixed in by
the view at runtime).
The declaration syntax at present is simply a list of tuples which is queried
by the view when a context menu is requested.

Following is an example declaring a single menu item to be displayed when
right-clicking on the controller's representation in the UI

.. code-block:: python

    bindings = [
        ('addAction', ('Properties', lambda: self._show_properties())),
    ]

The menu is built by iterating through the bindings list, each 2-tuple is a
tuple of the QMenu function to call ('addAction'), and the positional
arguments supplied to the function - in this case the name 'Properties', and
the lambda functor to call when activated.

.. contents::
    :depth: 2


Interfaces
----------

The following interfaces provide interface definitions for the various
controllers used within the overall project model.

The interfaces, while perhaps not exactly Pythonic, provide great utility
in terms of type safety in the interaction of the various controllers.
In most cases the concrete subclasses of these interfaces cannot be
directly imported into other controllers as this would cause circular
import loops


e.g. the :class:`~.flight_controller.FlightController`
is a child of an :class:`~.project_controllers.AirborneProjectController`,
but the FlightController also stores a typed reference to its parent
(creating a circular reference), the interfaces are designed to allow proper
type hinting within the development environment in such cases.


.. py:module:: dgp.core.controllers.controller_interfaces

.. autoclass:: AbstractController
    :show-inheritance:
    :undoc-members:

.. autoclass:: IAirborneController
    :show-inheritance:
    :undoc-members:

.. autoclass:: IFlightController
    :show-inheritance:
    :undoc-members:

.. autoclass:: IMeterController
    :show-inheritance:
    :undoc-members:

.. autoclass:: IDataSetController
    :show-inheritance:
    :undoc-members:


Controllers
-----------

**Concrete controller implementations**

.. py:module:: dgp.core.controllers.project_controllers
.. autoclass:: AirborneProjectController
    :undoc-members:
    :show-inheritance:

.. py:module:: dgp.core.controllers.flight_controller
.. autoclass:: FlightController
    :undoc-members:
    :show-inheritance:

.. py:module:: dgp.core.controllers.gravimeter_controller
.. autoclass:: GravimeterController
    :undoc-members:
    :show-inheritance:

.. py:module:: dgp.core.controllers.dataset_controller
.. autoclass:: DataSetController
    :undoc-members:
    :show-inheritance:

.. py:module:: dgp.core.controllers.datafile_controller
.. autoclass:: DataFileController
    :undoc-members:
    :show-inheritance:

Containers
----------

.. py:module:: dgp.core.controllers.project_containers
.. autoclass:: ProjectFolder
    :undoc-members:
    :show-inheritance:


Utility/Helper Modules
----------------------

.. autoclass:: dgp.core.controllers.controller_mixins.AttributeProxy
    :undoc-members:

.. automodule:: dgp.core.controllers.controller_helpers
    :undoc-members:

