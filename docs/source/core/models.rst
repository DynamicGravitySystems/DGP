dgp.core.models package
=======================

The models package contains and defines the various data classes that define
the logical structure of a 'Gravity Project'

Currently we are focused exclusively on providing functionality for
representing and processing an Airborne gravity survey/campaign.
In future support will be added for processing and managing Marine gravity
survey's/campaigns.

The following generally describes the class hierarchy of a typical Airborne project:

.. py:module:: dgp.core.models


|    :obj:`~.project.AirborneProject`
|    ├── :obj:`~.flight.Flight`
|    │   ├── :obj:`~.dataset.DataSet`
|    │   │   ├── :obj:`~.datafile.DataFile` -- Gravity
|    │   │   ├── :obj:`~.datafile.DataFile` -- Trajectory
|    │   │   └── :obj:`~.dataset.DataSegment` -- Container (Multiple)
|    │   └── :obj:`~.meter.Gravimeter` -- Link
|    └── :obj:`~.meter.Gravimeter`

-----------------------------------------

The project can have multiple :obj:`~.flight.Flight`, and each Flight can have
0 or more :obj:`~.flight.FlightLine`, :obj:`~.datafile.DataFile`, and linked
:obj:`~.meter.Gravimeter`.
The project can also define multiple Gravimeters, of varying type with specific
configuration files assigned to each.

Model Development Principles
----------------------------

- Classes in the core models should be kept as simple as possible.
- :class:`@properties` (getter/setter) are encouraged where state updates must
  accompany a value change
- Otherwise, simple attributes/fields are preferred
- Models may contain back-references (upwards in the hierarchy) only to their
  parent (using the 'magic' parent attribute) - otherwise the JSON serializer
  will complain.
- Any complex functions/transformations should be handled by the model's
  controller
- Data validation should be handled by the controller, not the model.
- A limited set of complex objects can be used and serialized in the model,
  support may be added as the need arises in the JSON serializer.
- Any field defined in a model's :attr:`__dict__` or :attr:`__slots__` is
  serialization by the ProjectEncoder, and consequently must be accepted
  by name (keyword argument) in the model constructor for de-serialization

Supported Complex Types
^^^^^^^^^^^^^^^^^^^^^^^

- :class:`pathlib.Path`
- :class:`datetime.datetime`
- :class:`datetime.date`
- :class:`dgp.core.oid.OID`
- All classes in :mod:`dgp.core.models`

See :class:`~dgp.core.models.project.ProjectDecoder` and
:class:`~dgp.core.models.project.ProjectEncoder` for implementation details.


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

dgp.core.models.datafile module
-------------------------------

.. automodule:: dgp.core.models.datafile
    :members:
    :undoc-members:

dgp.core.models.dataset module
------------------------------

.. versionadded:: 0.1.0
.. automodule:: dgp.core.models.dataset
    :members:
    :undoc-members:


