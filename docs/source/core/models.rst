dgp.core.models package
=======================

The dgp.core.models package contains and defines the various
data classes that define the logical structure of a 'Gravity Project'

Currently we are focused exclusively on providing functionality for
representing and processing an Airborne Gravity Survey/Campaign.

The following generally describes the class hierarchy of a typical Airborne project:

.. py:module:: dgp.core.models


|    :obj:`~.project.AirborneProject`
|    ├── :obj:`~.flight.Flight`
|    │   ├── :obj:`~.flight.FlightLine`
|    │   ├── :obj:`~.data.DataFile` -- Gravity
|    │   └── :obj:`~.data.DataFile` -- Trajectory
|    │   └── :obj:`~.meter.Gravimeter`
|    └── :obj:`~.meter.Gravimeter`

-----------------------------------------

The project can have multiple :obj:`~.flight.Flight`, and each Flight can have 0 or more
:obj:`~.flight.FlightLine`, :obj:`~.data.DataFile`, and linked :obj:`~.meter.Gravimeter`.
The project can also define multiple Gravimeters, of varying type with specific
configuration files assigned to each.


.. contents::
    :depth: 2


dgp.core.models.project module
------------------------------

.. autoclass:: dgp.core.models.project.GravityProject
    :undoc-members:

.. autoclass:: dgp.core.models.project.AirborneProject
    :undoc-members:
    :show-inheritance:

Project Serialization/De-Serialization Classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: dgp.core.models.project.ProjectEncoder
    :show-inheritance:

.. autoclass:: dgp.core.models.project.ProjectDecoder
    :show-inheritance:


dgp.core.models.meter module
----------------------------

.. versionadded:: 0.1.0
.. automodule:: dgp.core.models.meter
    :undoc-members:

dgp.core.models.flight module
-----------------------------

.. automodule:: dgp.core.models.flight
    :undoc-members:

dgp.core.models.data module
------------------------------

.. automodule:: dgp.core.models.data
    :members:
    :undoc-members:

