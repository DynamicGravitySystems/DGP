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


Interfaces
----------

The following interfaces provide interface definitions for the various
controllers used within the overall project model.

The interfaces, while perhaps not exactly Pythonic, provide great utility
in terms of type safety in the interaction of the various controllers.
In most cases the concrete subclasses of these interfaces cannot be
directly imported into other controllers as this would cause circular
import loops

.. py:module:: dgp.core.controllers

e.g. the :class:`~.flight_controller.FlightController`
is a child of an :class:`~.project_controllers.AirborneProjectController`,
but the FlightController also stores a typed reference to its parent
(creating a circular reference), the interfaces are designed to allow proper
type hinting within the development environment in such cases.


.. py:module:: dgp.core.controllers.controller_interfaces

.. autoclass:: IBaseController
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

.. autoclass:: IParent
    :undoc-members:

.. autoclass:: IChild
    :undoc-members:


Controllers
-----------

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

.. py:module:: dgp.core.controllers.datafile_controller
.. autoclass:: DataFileController
    :undoc-members:
    :show-inheritance:

.. py:module:: dgp.core.controllers.flightline_controller
.. autoclass:: FlightLineController
    :undoc-members:
    :show-inheritance:


Utility/Helper Modules
----------------------

.. autoclass:: dgp.core.controllers.controller_mixins.AttributeProxy
    :undoc-members:

.. automodule:: dgp.core.controllers.controller_helpers
    :undoc-members:



