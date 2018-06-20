# coding: utf-8

import os
import sys
import traceback
import pytest
from PyQt5 import QtCore
# from PyQt5.Qt import QApplication
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import dgp making the project available to test suite by relative import of this file
# e.g. from .context import dgp
import dgp


def excepthook(type_, value, traceback_):
    """This allows IDE to properly display unhandled exceptions which are
    otherwise silently ignored as the application is terminated.
    Override default excepthook with
    >>> sys.excepthook = excepthook

    See: http://pyqt.sourceforge.net/Docs/PyQt5/incompatibilities.html
    """
    traceback.print_exception(type_, value, traceback_)
    QtCore.qFatal('')


sys.excepthook = excepthook
APP = QApplication([])
