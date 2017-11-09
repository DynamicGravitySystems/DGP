# coding: utf-8

import os
import sys

sys.path.append(os.path.dirname(__file__))

# from dgp import resources_rc
from dgp import resources_rc
from PyQt5.QtWidgets import QApplication
from dgp.gui.splash import SplashScreen

"""Program Main Entry Point - Loads SplashScreen GUI"""
if __name__ == "__main__":
    # print("CWD: {}".format(os.getcwd()))
    app = QApplication(sys.argv)
    form = SplashScreen()
    sys.exit(app.exec_())
