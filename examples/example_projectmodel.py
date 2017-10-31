# coding: utf-8

import sys

from dgp import resources_rc

from PyQt5.uic import loadUiType
from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5.QtCore import QModelIndex, Qt

from dgp.gui.models import ProjectModel
from dgp.lib.project import AirborneProject, Flight, AT1Meter

tree_dialog, _ = loadUiType('treeview.ui')


"""This module serves as an example implementation and use of a ProjectModel with a QTreeView widget."""


class TreeTest(QDialog, tree_dialog):
    def __init__(self, project):
        super().__init__()
        self.setupUi(self)
        self.model = ProjectModel(project, self)
        self.model.rowsAboutToBeInserted.connect(self.insert)
        self.treeView.doubleClicked.connect(self.dbl_click)
        self.treeView.setModel(self.model)
        self.show()

    def insert(self, index, start, end):
        print("About to insert rows at {}:{}".format(start, end))

    def dbl_click(self, index: QModelIndex):
        obj = self.model.data(index, Qt.UserRole)
        print("Obj type: {}, obj: {}".format(type(obj), obj))
        # print(index.internalPointer().internal_pointer)


if __name__ == "__main__":
    prj = AirborneProject('.', 'TestTree')
    prj.add_flight(Flight(prj, 'Test Flight'))

    meter = AT1Meter('AT1M-6', g0=100, CrossCal=250)

    app = QApplication(sys.argv)
    dialog = TreeTest(prj)
    f3 = Flight(prj, "Test Flight 3")
    f3.add_line(0, 250)
    f3.add_line(251, 350)
    # print("F3: {}".format(f3))
    f3._gpsdata_uid = 'test1235'
    dialog.model.add_child(f3)
    # print(meter)
    dialog.model.add_child(meter)
    # print(len(project))
    # for flight in project.flights:
    #     print(flight)

    prj.add_flight(Flight(None, 'Test Flight 2'))
    dialog.model.remove_child(f3)
    # dialog.model.remove_child(f3)
    sys.exit(app.exec_())

