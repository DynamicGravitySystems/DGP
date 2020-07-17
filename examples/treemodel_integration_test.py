# -*- coding: utf-8 -*-
import datetime
import sys
import traceback
from itertools import count
from pathlib import Path
from pprint import pprint

from PyQt5 import QtCore

from dgp.core.models.dataset import DataSet
from dgp.core.oid import OID
from dgp.core.controllers.flight_controller import FlightController
from dgp.core.controllers.project_controllers import AirborneProjectController
from core.controllers.project_treemodel import ProjectTreeModel
from dgp.core.models.flight import Flight, FlightLine, DataFile
from dgp.core.models.meter import Gravimeter
from dgp.core.models.project import AirborneProject

from PyQt5.uic import loadUiType
from PyQt5.QtWidgets import QDialog, QApplication

from gui.views import ProjectTreeView

tree_dialog, _ = loadUiType('treeview.ui')


def excepthook(type_, value, traceback_):
    """This allows IDE to properly display unhandled exceptions which are
    otherwise silently ignored as the application is terminated.
    Override default excepthook with
    >>> sys.excepthook = excepthook

    See: http://pyqt.sourceforge.net/Docs/PyQt5/incompatibilities.html
    """
    traceback.print_exception(type_, value, traceback_)
    QtCore.qFatal('')


class TreeTestDialog(QDialog, tree_dialog):
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

    def _flight_changed(self, flight: FlightController):
        print("Setting fl model")
        self.cb_flight_lines.setModel(flight.lines_model)


if __name__ == "__main__":
    sys.excepthook = excepthook

    # Mock up a base project
    project = AirborneProject(name="Test Project", path=Path('.'), create_date=datetime.datetime(2018, 5, 12))
    flt = Flight('Test Flight', datetime.datetime(2018, 3, 9), uid=OID(base_uuid='0a193af02d1f46c6b8bad4dad028b3bc'))
    flt.add_child(FlightLine(datetime.datetime.now().timestamp(), datetime.datetime.now().timestamp() + 3600, 1))
    flt.add_child(DataSet())
    # first one is real reference in HDF5
    # flt.add_child(DataFile('gravity', datetime.datetime.today(),
    #                        source_path=Path('C:\\RealSample.txt'),
    #                        uid=OID(base_uuid='4458f26f6d7b4eb09097093dd2b85c61')))
    # flt.add_child(DataFile('gravity', datetime.datetime.today(), source_path=Path('C:\\data2.csv')))
    # flt.add_child(DataFile('trajectory', datetime.datetime.today(),
    #                        source_path=Path('C:\\trajectory1.dat')))
    at1a6 = Gravimeter('AT1A-6')
    at1a10 = Gravimeter('AT1A-10')
    project.add_child(at1a6)
    # project.add_child(flt)

    app = QApplication([])

    prj_ctrl = AirborneProjectController(project)
    model = ProjectTreeModel(prj_ctrl)
    # proxy_model = ProjectTreeProxyModel()
    # proxy_model.setSourceModel(model)
    # proxy_model.setFilterRole(Qt.UserRole)
    # proxy_model.setFilterType(Flight)

    dlg = TreeTestDialog(model)
    # dlg.qlv_proxy.setModel(proxy_model)
    prj_ctrl.set_parent_widget(dlg)
    fc = prj_ctrl.add_child(flt)
    dlg.qlv_0.setModel(fc.data_model)
    dlg.qlv_1.setModel(fc.data_model)

    counter = count(2)

    def add_line():
        for fc in prj_ctrl.flights.items():
            fc.add_child(FlightLine(datetime.datetime.now().timestamp(), datetime.datetime.now().timestamp() + 2400,
                                    next(counter)))

    # cn_select_dlg = ChannelSelectDialog(fc.data_model, plots=1)

    dlg.btn.clicked.connect(add_line)
    dlg.btn_export.clicked.connect(lambda: pprint(project.to_json(indent=4)))
    dlg.btn_flight.clicked.connect(lambda: prj_ctrl.add_flight())
    dlg.btn_gravimeter.clicked.connect(lambda: prj_ctrl.add_gravimeter())
    dlg.btn_importdata.clicked.connect(lambda: prj_ctrl.load_file_dlg())
    dlg.qpb_properties.clicked.connect(lambda: prj_ctrl.properties_dlg())
    dlg.show()
    prj_ctrl.add_child(at1a10)
    sys.exit(app.exec_())
