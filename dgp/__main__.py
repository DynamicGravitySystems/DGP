# coding: utf-8

import sys

from PyQt5 import QtWidgets

from dgp.gui.main import SplashScreen

"""Program Main Entry Point - Loads SplashScreen GUI"""
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    form = SplashScreen()
    sys.exit(app.exec_())
