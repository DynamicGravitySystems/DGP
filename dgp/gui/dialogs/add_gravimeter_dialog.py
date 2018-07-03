# -*- coding: utf-8 -*-
from pathlib import Path
from pprint import pprint
from typing import Optional

from PyQt5.QtGui import QIntValidator, QIcon, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QDialog, QWidget, QFileDialog, QListWidgetItem

from dgp.core.controllers.controller_interfaces import IAirborneController
from dgp.core.models.meter import Gravimeter
from dgp.gui.ui.add_meter_dialog import Ui_AddMeterDialog


class AddGravimeterDialog(QDialog, Ui_AddMeterDialog):
    def __init__(self, project: IAirborneController, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)
        self._project = project
        self._valid_ext = ('.ini', '.txt', '.conf')

        AT1A = QListWidgetItem(QIcon(":/icons/dgs"), "AT1A")
        AT1M = QListWidgetItem(QIcon(":/icons/dgs"), "AT1M")

        self.qlw_metertype.addItem(AT1A)
        self.qlw_metertype.addItem(AT1M)
        self.qlw_metertype.addItem("TAGS")
        self.qlw_metertype.addItem("ZLS")
        self.qlw_metertype.addItem("AirSeaII")
        self.qlw_metertype.currentRowChanged.connect(self._type_changed)
        self.qlw_metertype.setCurrentRow(0)

        self.qtb_browse_config.clicked.connect(self._browse_config)
        self.qle_config_path.textChanged.connect(self._path_changed)
        self.qle_serial.textChanged.connect(lambda text: self._serial_changed(text))
        self.qle_serial.setValidator(QIntValidator(1, 1000))

        self._config_model = QStandardItemModel()
        self._config_model.itemChanged.connect(self._config_data_changed)

        self.qtv_config_view.setModel(self._config_model)

    @property
    def config_path(self):
        if not len(self.qle_config_path.text()):
            return None
        _path = Path(self.qle_config_path.text())
        if not _path.exists():
            return None
        if not _path.is_file():
            return None
        if _path.suffix not in self._valid_ext:
            return None
        return _path

    def accept(self):
        if self.qle_config_path.text():
            meter = Gravimeter.from_ini(Path(self.qle_config_path.text()), name=self.qle_name.text())
        else:
            meter = Gravimeter(self.qle_name.text())
        self._project.add_child(meter)

        super().accept()

    def _path_changed(self, text: str):
        if self.config_path is not None and self.config_path.exists():
            self._preview_config()

    def get_sensor_type(self) -> str:
        return self.qlw_metertype.currentItem().text()

    def _browse_config(self):  # pragma: no cover
        # TODO: Look into useing getOpenURL methods for files on remote/network drives
        path, _ = QFileDialog.getOpenFileName(self, "Select Configuration File", str(Path().resolve()),
                                              "Configuration (*.ini);;Any (*.*)")
        if path:
            self.qle_config_path.setText(path)

    def _config_data_changed(self, item: QStandardItem):  # pragma: no cover
        # TODO: Implement this if desire to enable editing of config from the preview table
        index = self._config_model.index(item.row(), item.column())
        sibling = self._config_model.index(item.row(), 0 if item.column() else 1)

    def _preview_config(self):
        if self.config_path is None:
            return
        config = Gravimeter.read_config(self.config_path)

        self._config_model.clear()
        self._config_model.setHorizontalHeaderLabels(["Config Key", "Value"])
        for key, value in config.items():
            self._config_model.appendRow([QStandardItem(key), QStandardItem(str(value))])

    def _type_changed(self, row: int):
        self._serial_changed(self.qle_serial.text())

    def _serial_changed(self, text: str):
        self.qle_name.setText("%s-%s" % (self.get_sensor_type(), text))
