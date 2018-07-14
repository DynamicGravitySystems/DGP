User Guide
==========

.. todo:: Write documentation/tutorial on how to use the application,
          targeted at actual users, not developers.

Creating a new project
----------------------


Project Structure (Airborne)
++++++++++++++++++++++++++++

An Airborne gravity project in DGP is centered primarily around the
:obj:`Flight` construct as a representation of an actual survey flight. A
flight has at least one :obj:`DataSet` containing Trajectory (GPS) and Gravity
data files, and at least one associated :obj:`Gravimeter`.

A :obj:`Flight` may potentially have more than one :obj:`DataSet` associated
with it, and more than one :obj:`Gravimeter`.

Each DataSet has exactly one Trajectory and one Gravity DataFile contained
within it, and the :obj:`DataSet` may define :obj:`DataSegments` which are
directly associated with the encapsulated files.

DataSegments are used to select areas of data which are of interest for
processing, typically this means they are used to select the individual
Flight Lines out of a continuous data file, i.e. the segments between course
changes of the aircraft.




Creating Flights/Survey's
-------------------------


Importing Gravimeter (Sensor) Configurations
--------------------------------------------


Importing Gravity/Trajectory (GPS) Data
---------------------------------------



Data Processing Workflow
------------------------

Selecting Survey Lines
++++++++++++++++++++++


Selecting/Applying Transformation Graphs
++++++++++++++++++++++++++++++++++++++++


Viewing Line Repeats
++++++++++++++++++++
