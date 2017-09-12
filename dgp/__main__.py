# coding: utf-8

import sys
import time

from dgp import resources_rc
from PyQt5.QtWidgets import QApplication, QSplashScreen

from dgp.gui.splash import SplashScreen

"""Program Main Entry Point - Loads SplashScreen GUI"""
if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = SplashScreen()
    sys.exit(app.exec_())
