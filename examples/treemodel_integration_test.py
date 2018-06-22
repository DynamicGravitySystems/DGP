# coding: utf-8

import sys
import traceback
from itertools import count
from pathlib import Path
from pprint import pprint

from PyQt5 import QtCore
from PyQt5.QtGui import QStandardItemModel

from core.controllers.ProjectController import AirborneProjectController
from core.models.ProjectTreeModel import ProjectTreeModel
from core.models.flight import Flight, FlightLine, DataFile
from core.models.project import AirborneProject

from PyQt5.uic import loadUiType
from PyQt5.QtWidgets import QDialog, QApplication

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
        self.treeView.expandAll()


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
    sys.excepthook = excepthook

    project = AirborneProject(name="Test Project", path=Path('.'))
    flt = Flight('Test Flight')
    flt.add_flight_line(FlightLine(23, 66, 1))
    flt.add_child(DataFile('/flights/gravity/1234', 'Test File', 'gravity'))
    project.add_child(flt)

    prj_item = AirborneProjectController(project)

    model = ProjectTreeModel()
    model.appendRow(prj_item)

    app = QApplication([])
    dlg = TreeTest(model)

    counter = count(2)

    def add_line():
        for fc in prj_item.flight_controllers:
            fc.add_child(FlightLine(next(counter), next(counter), next(counter)))


    dlg.btn.clicked.connect(add_line)
    dlg.btn_export.clicked.connect(lambda: pprint(project.to_json(indent=4)))
    dlg.btn_flight.clicked.connect(lambda: prj_item.add_flight(Flight('Flight %d' % next(counter))))
    dlg.show()
    sys.exit(app.exec_())
