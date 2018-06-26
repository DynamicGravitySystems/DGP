# -*- coding: utf-8 -*-

import sys
import traceback
from itertools import count
from pathlib import Path
from pprint import pprint

from PyQt5 import QtCore

from core.controllers.FlightController import FlightController, StandardFlightItem
from core.controllers.ProjectController import AirborneProjectController
from core.models.ProjectTreeModel import ProjectTreeModel
from core.models.flight import Flight, FlightLine, DataFile
from core.models.meter import Gravimeter
from core.models.project import AirborneProject

from PyQt5.uic import loadUiType
from PyQt5.QtWidgets import QDialog, QApplication

from core.views import ProjectTreeView

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

        self.treeView: ProjectTreeView

        self.treeView.setModel(model)
        model.flight_changed.connect(self._flight_changed)
        self.treeView.expandAll()

        self._cmodel = None

    def _flight_changed(self, flight: FlightController):
        print("Setting fl model")
        self._cmodel = flight.lines_model
        print(self._cmodel)
        print(self._cmodel.rowCount())
        print(self._cmodel.item(0))
        self.cb_flight_lines.setModel(self._cmodel)


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
    flt.add_child(FlightLine(23, 66, 1))
    flt.add_child(DataFile('/flights/gravity/1234', 'Test File', 'gravity'))
    at1a6 = Gravimeter('AT1A-6')
    at1a10 = Gravimeter('AT1A-10')

    project.add_child(at1a6)
    project.add_child(flt)

    prj_ctrl = AirborneProjectController(project)

    model = ProjectTreeModel(prj_ctrl)

    app = QApplication([])
    # app = QGuiApplication(sys.argv)

    dlg = TreeTest(model)

    counter = count(2)

    def add_line():
        for fc in prj_ctrl.flight_ctrls:
            fc.add_child(FlightLine(next(counter), next(counter), next(counter)))


    dlg.btn.clicked.connect(add_line)
    dlg.btn_export.clicked.connect(lambda: pprint(project.to_json(indent=4)))
    dlg.btn_flight.clicked.connect(lambda: prj_ctrl.add_child(Flight('Flight %d' % next(counter))))
    dlg.show()
    prj_ctrl.add_child(at1a10)
    sys.exit(app.exec_())
