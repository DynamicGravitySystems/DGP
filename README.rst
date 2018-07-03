DGP (Dynamic Gravity Processor)
===============================
.. image:: https://travis-ci.org/DynamicGravitySystems/DGP.svg?branch=master
    :target: https://travis-ci.org/DynamicGravitySystems/DGP

.. image:: https://coveralls.io/repos/github/DynamicGravitySystems/DGP/badge.svg?branch=feature%2Fproject-structure
    :target: https://coveralls.io/github/DynamicGravitySystems/DGP?branch=feature%2Fproject-structure

.. image:: https://ci.appveyor.com/api/projects/status/np3s77n1s8hpvn5u?svg=true
    :target: https://ci.appveyor.com/api/projects/status/np3s77n1s8hpvn5u?svg=true

What is it
----------
**DGP** is an library as well an application for processing gravity data collected
with dynamic gravity systems, such as those run on ships and aircraft.

The library can be used to automate the processing workflow and experiment with
new techniques. The application was written to fulfill the needs of of gravity
processing in production environment.

The project aims to bring all gravity data processing under a single umbrella by:

- accommodating various sensor types, data formats, and processing techniques
- providing a flexible framework to allow for experimentation with the workflow
- providing a robust and efficient system for production-level processing

Dependencies
------------
- numpy >= 1.13.1
- pandas >= 0.20.3
- scipy >= 0.19.1
- matplotlib >= 2.0.2
- PyQt5 >= 5.9
- PyTables_ >= 3.0.0

.. _PyTables: http://www.pytables.org

License
-------
`Apache License, Version 2.0`_

.. _`Apache License, Version 2.0`: https://www.apache.org/licenses/LICENSE-2.0

Documentation
-------------
The Sphinx documentation included in the repository and hosted on readthedocs_
should provide a good starting point for learning how to use the library.

.. _readthedocs: http://dgp.readthedocs.io/en/latest/

Documentation on how to use the application to follow.

Contributing to DGP
-------------------
All contributions in the form of bug reports, bug fixes, documentation
improvements, enhancements, and ideas are welcome.

If you would like to contribute in any of these ways, then you can start at
the `GitHub "issues" tab`_. A detailed guide on how to contribute can be found
here_.

.. _`GitHub "issues" tab`: https://github.com/DynamicGravitySystems/DGP/issues
.. _here: http://dgp.readthedocs.io/en/latest/contributing.html
