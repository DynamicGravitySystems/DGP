# -*- coding: utf-8 -*-
import os
from pprint import pprint
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator, QIcon
from PyQt5.QtWidgets import QDialog, QWidget, QFileDialog, QListWidgetItem

from dgp.core.controllers.controller_interfaces import IAirborneController
from dgp.core.models.meter import Gravimeter
from dgp.gui.ui.add_meter_dialog import Ui_AddMeterDialog


class AddGravimeterDialog(QDialog, Ui_AddMeterDialog):
    def __init__(self, project: IAirborneController, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)
        self._project = project

        AT1A = QListWidgetItem(QIcon(":/icons/dgs"), "AT1A")
        AT1M = QListWidgetItem(QIcon(":/icons/dgs"), "AT1M")

        self.qlw_metertype.addItem(AT1A)
        self.qlw_metertype.addItem(AT1M)
        self.qlw_metertype.addItem("TAGS")
        self.qlw_metertype.addItem("ZLS")
        self.qlw_metertype.addItem("AirSeaII")
        self.qlw_metertype.setCurrentRow(0)
        self.qlw_metertype.currentRowChanged.connect(self._type_changed)

        self.qtb_browse_config.clicked.connect(self._browse_config)
        self.qle_serial.textChanged.connect(lambda text: self._serial_changed(text))
        self.qle_serial.setValidator(QIntValidator(1, 1000))
        # self.qle_config_path.textChanged.connect(lambda text: self._text_changed(text))

    def get_sensor_type(self) -> str:
        item = self.qlw_metertype.currentItem()
        if item is not None:
            return item.text()

    def _browse_config(self):
        # TODO: Look into useing getOpenURL methods for files on remote/network drives
        path, _ = QFileDialog.getOpenFileName(self, "Select Configuration File", os.getcwd(),
                                              "Configuration (*.ini);;Any (*.*)")
        if path:
            self.qle_config_path.setText(path)

    def _type_changed(self, row: int):
        self._serial_changed(self.qle_serial.text())

    def _serial_changed(self, text: str):
        self.qle_name.setText("%s-%s" % (self.get_sensor_type(), text))

    def accept(self):
        if self.qle_config_path.text():
            meter = Gravimeter.from_ini(self.qle_config_path.text())
            pprint(meter.config)
        else:
            meter = Gravimeter(self.qle_name.text())
        self._project.add_child(meter)

        super().accept()
