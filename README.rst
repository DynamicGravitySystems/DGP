DGP (Dynamic Gravity Processor)
===============================
.. image:: https://travis-ci.org/DynamicGravitySystems/DGP.svg?branch=master
    :target: https://travis-ci.org/DynamicGravitySystems/DGP

-------------------
Package Structure
-------------------
1. dgp
    1. lib
        1. gravity_ingestor.py - Functions for importing Gravity data
        2. trajectory_ingestor.py - Functions for importing GPS (Trajectory) data
    2. ui
        - Contains all Qt Designer UI files and resources
    3. main.pyw - Primary GUI classes and code
    4. loader.py - GUI Threading code
    5. resources_rc.py - Compiled PyQt resources file
2. docs
3. tests
