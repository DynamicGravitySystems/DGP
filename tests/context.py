# coding: utf-8

import os
import sys
from PyQt5.Qt import QApplication
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import dgp making the project available to test suite by relative import of this file
# e.g. from .context import dgp

import dgp

APP = QApplication([])
