# coding: utf-8

import sys
import traceback

from PyQt5 import sip
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QStyleFactory
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


app = None


def main():
    global app
    QApplication.setStyle(QStyleFactory.create("Fusion"))
    sys.excepthook = excepthook
    app = QApplication(sys.argv)
    form = SplashScreen()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
