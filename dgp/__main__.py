# coding: utf-8

import os
import sys
import traceback

sys.path.append(os.path.dirname(__file__))

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from dgp.gui.splash import SplashScreen


def excepthook(type_, value, traceback_):
    """This allows IDE to properly display unhandled exceptions which are
    otherwise silently ignored as the application is terminated.
    Override default excepthook with
    >>> sys.excepthook = excepthook

    See: http://pyqt.sourceforge.net/Docs/PyQt5/incompatibilities.html
    """
    traceback.print_exception(type_, value, traceback_)
    QtCore.qFatal('')


"""Program Main Entry Point - Loads SplashScreen GUI"""
if __name__ == "__main__":
    sys.excepthook = excepthook
    app = QApplication(sys.argv)
    form = SplashScreen()
    sys.exit(app.exec_())
