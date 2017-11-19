# coding: utf-8

import sys
from pathlib import Path

from dgp import resources_rc

from PyQt5.uic import loadUiType
from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5.QtCore import QModelIndex, Qt

from dgp.gui.models import ProjectModel
from dgp.lib.types import TreeItem
from dgp.gui.qtenum import QtDataRoles
from dgp.lib.project import AirborneProject, Flight, AT1Meter, Container, \
    MeterConfig

tree_dialog, _ = loadUiType('treeview_testing.ui')


class TreeTest(QDialog, tree_dialog):
    """
    Tree GUI Members:
    treeViewTop : QTreeView
    treeViewBtm : QTreeView
    button_add : QPushButton
    button_delete : QPushButton
    """
    def __init__(self, project):
        super().__init__()
        self.setupUi(self)
        self._prj = project
        self._last_added = None

        model = ProjectModel(project, self)
        self.button_add.clicked.connect(self.add_flt)
        self.button_delete.clicked.connect(self.rem_flt)
        self.treeViewTop.doubleClicked.connect(self.dbl_click)
        self.treeViewTop.setModel(model)
        # self.treeViewTop.expandAll()
        self.show()

    def add_flt(self):
        nflt = Flight(self._prj, "Testing Dynamic {}".format(
            self._prj.count_flights))
        self._prj.add_flight(nflt)
        self._last_added = nflt
        # self.expand()

    def rem_flt(self):
        if self._last_added is not None:
            print("Removing flight")
            self._prj.remove_flight(self._last_added)
            self._last_added = None
        else:
            print("No flight to remove")

    def expand(self):
        self.treeViewTop.expandAll()
        self.treeViewBtm.expandAll()

    def dbl_click(self, index: QModelIndex):
        internal = index.internalPointer()
        print("Object: ", internal)
        # print(index.internalPointer().internal_pointer)


class SimpleItem(TreeItem):
    def __init__(self, uid, parent=None):
        super().__init__(str(uid), parent=parent)

    def data(self, role: QtDataRoles):
        if role == QtDataRoles.DisplayRole:
            return self.uid


if __name__ == "__main__":
    prj = AirborneProject('.', 'TestTree')
    prj.add_flight(Flight(prj, 'Test Flight'))

    meter = AT1Meter('AT1M-6', g0=100, CrossCal=250)

    app = QApplication(sys.argv)
    dialog = TreeTest(prj)

    f3 = Flight(prj, "Test Flight 3")
    # f3.add_line(0, 250)
    # f3.add_line(251, 350)
    prj.add_flight(f3)
    f3index = dialog.treeViewTop.model().index_from_item(f3)

    print("F3 ModelIndex: ", f3index)
    print("F3 MI row {} obj {}".format(f3index.row(),
                                          f3index.internalPointer()))
    # print("F3: {}".format(f3))
    # f3._gpsdata_uid = 'test1235'
    # dialog.model.add_child(f3)
    # print(meter)
    # dialog.model.add_child(meter)
    # print(len(project))
    # for flight in project.flights:
    #     print(flight)

    # prj.add_flight(Flight(None, 'Test Flight 2'))
    # dialog.model.remove_child(f3)
    # dialog.model.remove_child(f3)

    sys.exit(app.exec_())

