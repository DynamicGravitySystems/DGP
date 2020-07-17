Welcome to Dynamic Gravity Processor's documentation!
=====================================================

What is DGP?
^^^^^^^^^^^^

**DGP** is a library as well a graphical desktop application for processing
gravity data collected with dynamic gravity systems, such as those run on
ships and aircraft.

The library can be used to automate the processing workflow and experiment with
new techniques. The application was written to fulfill the needs of of gravity
processing in production environments.

The project aims to bring all gravity data processing under a single umbrella by:

- accommodating various sensor types, data formats, and processing techniques
- providing a flexible framework to allow for experimentation with the workflow
- providing a robust and efficient system for production-level processing

Core Dependencies
+++++++++++++++++

(Subject to change)

- Python >= 3.6
- numpy >= 1.13.1
- pandas == 0.20.3
- scipy == 1.1.0
- pyqtgraph >= 0.10.0
- PyQt5 >= 5.10
- PyTables >= 3.4.2

.. toctree::
   :caption: Getting Started
   :maxdepth: 1

   install.rst
   userguide.rst

.. toctree::
   :caption: API Documentation

   core/index.rst
   lib/index.rst
   gui/index.rst
   core/data-management.rst

.. toctree::
   :caption: Development

   contributing.rst
   requirements-specification-include.rst
   todo.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
