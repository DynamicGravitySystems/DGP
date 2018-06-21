# coding: utf-8

import sys
import traceback
from pathlib import Path

from PyQt5 import QtCore
from PyQt5.QtGui import QStandardItem, QIcon, QStandardItemModel

from core.controllers.FlightController import FlightController
from core.flight import Flight, FlightLine
from dgp import resources_rc

from PyQt5.uic import loadUiType
from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5.QtCore import QModelIndex, Qt


tree_dialog, _ = loadUiType('treeview.ui')


class TreeTest(QDialog, tree_dialog):
    """
    Tree GUI Members:
    treeViewTop : QTreeView
    treeViewBtm : QTreeView
    button_add : QPushButton
    button_delete : QPushButton
    """

    def __init__(self, model):
        super().__init__(parent=None)
        self.setupUi(self)
        self.treeView.setModel(model)


def excepthook(type_, value, traceback_):
    """This allows IDE to properly display unhandled exceptions which are
    otherwise silently ignored as the application is terminated.
    Override default excepthook with
    >>> sys.excepthook = excepthook

    See: http://pyqt.sourceforge.net/Docs/PyQt5/incompatibilities.html
    """
    traceback.print_exception(type_, value, traceback_)
    QtCore.qFatal('')


if __name__ == "__main__":
    flt = Flight('Test Flight')
    flt.add_flight_line(FlightLine('then', 'now', 1))
    flt_ctrl = FlightController(flt)

    root_item = QStandardItem("ROOT")
    # atm = AbstractTreeModel(root_item)
    atm = QStandardItemModel()
    atm.appendRow(root_item)
    flights = QStandardItem("Flights")
    root_item.appendRow(flights)

    flights.appendRow(flt_ctrl)

    sys.excepthook = excepthook
    app = QApplication([])
    dlg = TreeTest(atm)

    dlg.btn.clicked.connect(lambda: flt_ctrl.add_flight_line(FlightLine('yesterday', 'today', 2)))
    # dlg.btn.clicked.connect(lambda: atm.update())
    dlg.show()
    sys.exit(app.exec_())
