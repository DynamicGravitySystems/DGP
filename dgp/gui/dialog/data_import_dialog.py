# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from pathlib import Path
from typing import Union

from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QDate
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import QDialog, QFileDialog, QListWidgetItem, QCalendarWidget

import dgp.core.controllers.gravimeter_controller as mtr
from dgp.core.controllers.controller_interfaces import IAirborneController
from dgp.core.controllers.flight_controller import FlightController
from dgp.gui.ui.data_import_dialog import Ui_DataImportDialog
from dgp.core.models.data import DataFile
from dgp.core.types.enumerations import DataTypes


class DataImportDialog(QDialog, Ui_DataImportDialog):
    load = pyqtSignal(DataFile)

    def __init__(self, controller: IAirborneController, datatype: DataTypes, base_path: str = None, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.log = logging.getLogger(__name__)

        self._controller = controller
        self._datatype = datatype
        self._base_path = base_path or str(Path().home().resolve())
        self._type_map = {DataTypes.GRAVITY: 0, DataTypes.TRAJECTORY: 1}
        self._type_filters = {DataTypes.GRAVITY: "Gravity (*.dat *.csv);;Any (*.*)",
                              DataTypes.TRAJECTORY: "Trajectory (*.dat *.csv *.txt);;Any (*.*)"}

        self._gravity = QListWidgetItem("Gravity")
        self._gravity.setData(Qt.UserRole, DataTypes.GRAVITY)
        self._trajectory = QListWidgetItem("Trajectory")
        self._trajectory.setData(Qt.UserRole, DataTypes.TRAJECTORY)

        self.qlw_datatype.addItem(self._gravity)
        self.qlw_datatype.addItem(self._trajectory)
        self.qlw_datatype.setCurrentRow(self._type_map.get(datatype, 0))

        self._flight_model = self._controller.flight_model  # type: QStandardItemModel
        self.qcb_flight.setModel(self._flight_model)
        self.qde_date.setDate(datetime.today())
        self._calendar = QCalendarWidget()
        self.qde_date.setCalendarWidget(self._calendar)
        self.qde_date.setCalendarPopup(True)

        # Gravity Widget
        self.qcb_gravimeter.currentIndexChanged.connect(self._gravimeter_changed)
        self._meter_model = self._controller.meter_model  # type: QStandardItemModel
        self.qcb_gravimeter.setModel(self._meter_model)
        self.qpb_add_sensor.clicked.connect(self._controller.add_gravimeter)
        if self._meter_model.rowCount() == 0:
            print("NO meters available")
        self.qcb_gravimeter.setCurrentIndex(0)

        # Trajectory Widget

        # Signal connections
        self.qlw_datatype.currentItemChanged.connect(self._datatype_changed)
        self.qpb_browse.clicked.connect(self._browse)
        self.qpb_add_flight.clicked.connect(self._controller.add_flight)

    def set_initial_flight(self, flight):
        print("Setting initial flight to: " + str(flight))
        if flight is None:
            return

    def _load_gravity(self, flt: FlightController):
        col_fmt = self.qle_grav_format.text()
        file = DataFile(flt.uid.base_uuid, 'gravity', self.date, self.file_path, col_fmt)

        # Important: We need to retrieve the ACTUAL flight controller, not the clone
        fc = self._controller.get_child_controller(flt.proxied)
        fc.add_child(file)
        self.load.emit(file)

    def _load_trajectory(self):
        pass

    @property
    def file_path(self) -> Union[Path, None]:
        if not len(self.qle_filepath.text()):
            return None
        return Path(self.qle_filepath.text())

    @property
    def datatype(self) -> DataTypes:
        return self.qlw_datatype.currentItem().data(Qt.UserRole)

    @property
    def _browse_path(self):
        return self.file_path or self._base_path

    @property
    def date(self) -> datetime:
        _date: QDate = self.qde_date.date()
        return datetime(_date.year(), _date.month(), _date.day())

    def accept(self):
        if self.file_path is None:
            self.ql_path.setStyleSheet("color: red")
            self.log.warning("Path cannot be empty.")
            return
        if not self.file_path.exists():
            self.ql_path.setStyleSheet("color: red")
            self.log.warning("Path does not exist.")
            return
        if not self.file_path.is_file():
            self.ql_path.setStyleSheet("color: red")
            self.log.warning("Path must be a file, not a directory.")

        # Note: This FlightController is a Clone
        fc = self._flight_model.item(self.qcb_flight.currentIndex())

        if self.datatype == DataTypes.GRAVITY:
            self._load_gravity(fc)
            return super().accept()
        elif self.datatype == DataTypes.TRAJECTORY:
            self._load_trajectory()
            return super().accept()

        self.log.error("Unknown Datatype supplied to import dialog. %s", str(self.datatype))
        return super().accept()

    @pyqtSlot(name='_browse')
    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Browse for data file", str(self._browse_path),
                                              self._type_filters[self._datatype])
        if path:
            self.qle_filepath.setText(path)

    @pyqtSlot(QListWidgetItem, QListWidgetItem, name='_datatype_changed')
    def _datatype_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        self._datatype = current.data(Qt.UserRole)
        self.qsw_advanced_properties.setCurrentIndex(self._type_map[self._datatype])

    @pyqtSlot(int, name='_gravimeter_changed')
    def _gravimeter_changed(self, index: int):
        meter_ctrl = self._controller.meter_model.item(index)
        if not meter_ctrl:
            self.log.debug("No meter available")
            return
        if isinstance(meter_ctrl, mtr.GravimeterController):
            sensor_type = meter_ctrl.sensor_type or "Unknown"
            self.qle_sensortype.setText(sensor_type)
            self.qle_grav_format.setText(meter_ctrl.column_format)
